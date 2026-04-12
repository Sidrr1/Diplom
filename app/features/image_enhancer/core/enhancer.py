import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

MAX_OUTPUT_PX = 2560

SUPPORTED_EXT = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".webp",
    ".tiff", ".tif", ".gif", ".ico", ".ppm", ".pgm", ".pbm", ".dib"
}


def open_image(path: str) -> Image.Image:
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        img.seek(0)
    return img.convert("RGB")


def _assess_quality(img: Image.Image) -> dict:
    arr = np.array(img.convert("L"), dtype=np.float32)
    lap = cv2.Laplacian(arr.astype(np.uint8), cv2.CV_64F)
    blur = cv2.GaussianBlur(arr.astype(np.uint8), (5, 5), 0)
    return {
        "sharpness": lap.var(),
        "noise":     np.abs(arr - blur).mean(),
        "contrast":  arr.std(),
        "is_low_res": img.width * img.height < 480 * 360,
    }


def _upscale_script(img: Image.Image, progress_cb=None) -> Image.Image:
    """Fallback: LANCZOS upscale."""
    w, h = img.size
    long_side = max(w, h)
    if long_side >= MAX_OUTPUT_PX:
        if progress_cb: progress_cb(75)
        return img.copy()
    scale = min(MAX_OUTPUT_PX / long_side, 4.0)
    tw, th = int(w * scale), int(h * scale)
    if progress_cb: progress_cb(30)
    if scale > 2.0 and w * h < 480 * 360:
        mid = img.resize((w * 2, h * 2), Image.LANCZOS)
        result = mid.resize((tw, th), Image.LANCZOS)
    else:
        result = img.resize((tw, th), Image.LANCZOS)
    if progress_cb: progress_cb(75)
    return result




def enhance(img: Image.Image, fidelity: float = 0.7, intensity: float = 1.0,
            progress_cb=None) -> tuple[Image.Image, str]:
    """
    Semantic-aware enhancement pipeline.

    Слой 1: Грубая сегментация (до апскейла)
    Слой 2: SwinIR x4 апскейл
    Слой 3: Точная сегментация (после апскейла)
    Слой 4: Зональная обработка
    Слой 5: Композит

    Args:
        img: входное изображение
        fidelity: баланс генерация/похожесть для CodeFormer (0.0-1.0)
        intensity: интенсивность эффекта (0.0-1.0)
        progress_cb: callback для прогресса

    Returns:
        (улучшенное изображение, информация)
    """
    print("[enhancer] === START ===")
    from .model_manager import get_model_manager
    from .image_analyzer import analyze_image
    from .regional_processor import RegionalProcessor
    from .zone_processor import ZoneProcessor
    from .post_processor import PostProcessor

    w, h = img.size

    if progress_cb: progress_cb(5)

    try:
        # Анализ изображения
        stats = analyze_image(img)
        if progress_cb: progress_cb(8)

        manager = get_model_manager()

        # Проверяем наличие моделей
        models_status = manager.check_models_exist()
        if not all(models_status.values()):
            missing = [k for k, v in models_status.items() if not v]
            print(f"[enhancer] Missing models: {missing}")
            raise Exception(f"Missing models: {missing}")

        # === СЛОЙ 1: Грубая сегментация (до апскейла) ===
        print("[enhancer] Layer 1: Coarse segmentation")
        segmentor = manager.get_segmentor()
        coarse_masks = segmentor.segment(img)
        if progress_cb: progress_cb(12)

        # Детекция лиц на оригинале
        detector = manager.get_face_detector()
        coarse_faces = detector.detect_faces(img, confidence_threshold=0.8)
        print(f"[enhancer] Layer 1: Detected {len(coarse_faces)} faces (coarse)")
        if progress_cb: progress_cb(15)

        # Адаптивная предобработка
        preprocessed = img
        if stats['needs_denoise']:
            print(f"[enhancer] Applying denoise (strength={stats['denoise_strength']})")
            arr = cv2.cvtColor(np.array(preprocessed), cv2.COLOR_RGB2BGR)
            arr = cv2.fastNlMeansDenoisingColored(
                arr, None,
                h=stats['denoise_strength'],
                hColor=stats['denoise_strength'],
                templateWindowSize=7,
                searchWindowSize=21
            )
            preprocessed = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        if stats['needs_contrast_boost']:
            print(f"[enhancer] Applying contrast boost (CLAHE={stats['clahe_clip']:.1f})")
            arr = cv2.cvtColor(np.array(preprocessed), cv2.COLOR_RGB2BGR)
            lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=stats['clahe_clip'], tileGridSize=(8, 8))
            l = clahe.apply(l)
            arr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
            preprocessed = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        if progress_cb: progress_cb(20)

        # === СЛОЙ 2: SwinIR x4 апскейл ===
        print("[enhancer] Layer 2: SwinIR x4 upscale")
        swinir = manager.get_swinir_upscaler(scale=4)
        upscaled = swinir.upscale(preprocessed, tile_size=512)
        print(f"[enhancer] Layer 2: {w}x{h} -> {upscaled.size[0]}x{upscaled.size[1]}")
        if progress_cb: progress_cb(45)

        # === СЛОЙ 3: Точная сегментация (после апскейла) ===
        print("[enhancer] Layer 3: Fine segmentation")
        fine_masks = segmentor.segment(upscaled)
        if progress_cb: progress_cb(50)

        # Детекция лиц на апскейленном
        fine_faces = detector.detect_faces(upscaled, confidence_threshold=0.8)
        print(f"[enhancer] Layer 3: Detected {len(fine_faces)} faces (fine)")
        if progress_cb: progress_cb(55)

        # Сопоставление: если количество лиц изменилось — используем fine
        if len(fine_faces) != len(coarse_faces):
            print(f"[enhancer] Layer 3: Face count mismatch (coarse={len(coarse_faces)}, fine={len(fine_faces)}), using fine")

        faces = fine_faces
        face_bboxes = [face['bbox'] for face in faces]

        # === СЛОЙ 3.5: Landmark Analysis ===
        print("[enhancer] Layer 3.5: Landmark analysis")
        from .landmark_analyzer import LandmarkAnalyzer
        landmark_analyzer = LandmarkAnalyzer()

        face_landmarks = []
        for i, face_bbox in enumerate(face_bboxes):
            landmarks = landmark_analyzer.analyze(upscaled, face_bbox)
            face_landmarks.append(landmarks)
            if landmarks['found']:
                print(f"[enhancer] Face {i+1}: {len(landmarks['landmarks'])} landmarks, confidence: {landmarks['confidence']:.2f}")
            else:
                print(f"[enhancer] Face {i+1}: Using anthropometric fallback")

        if progress_cb: progress_cb(60)

        if not faces:
            print("[enhancer] No faces detected, applying zone processing to whole image")
            # Зональная обработка без лиц
            result = _apply_zone_processing_no_faces(upscaled, fine_masks, intensity)

            # Frequency separation для сохранения деталей
            print("[enhancer] Applying frequency separation (no faces)")
            from .frequency_separation import frequency_separation
            result = frequency_separation(
                original=upscaled,
                enhanced=result,
                blur_radius=3.0,
                detail_strength=0.9  # Больше деталей оригинала для фона
            )

            if progress_cb: progress_cb(100)

            tw, th = result.size
            info = f"{w}x{h} -> {tw}x{th}  [SwinIR x4 + Zones + FreqSep]  Q:{stats['quality_score']:.1f}/10"
            print("[enhancer] === END ===")
            return result, info

        # === СЛОЙ 4: Зональная обработка ===
        print("[enhancer] Layer 4: Zone processing")

        # 4a: Региональная обработка лиц (CodeFormer + детали)
        processor = RegionalProcessor(manager)
        result = processor.process_regions(
            original=img,
            upscaled=upscaled,
            face_bboxes=face_bboxes,
            fidelity=fidelity
        )
        if progress_cb: progress_cb(70)

        # 4b: Landmark-based зональная обработка
        print("[enhancer] Layer 4b: Landmark-based zone processing")
        from .landmark_processor import LandmarkProcessor
        landmark_proc = LandmarkProcessor()

        for i, (face_bbox, landmarks) in enumerate(zip(face_bboxes, face_landmarks)):
            if landmarks['zones']:
                print(f"[enhancer] Processing {len(landmarks['zones'])} zones for face {i+1}")
                result = landmark_proc.process_face_zones(
                    result,
                    landmarks,
                    face_bbox,
                    intensity=intensity
                )

        if progress_cb: progress_cb(85)

        # 4c: Зональная обработка остальных областей (фон, небо, одежда)
        result = _apply_zone_processing_with_faces(
            result, fine_masks, face_bboxes, intensity
        )
        if progress_cb: progress_cb(90)

        # === ПОСТОБРАБОТКА: Коррекция артефактов ===
        print("[enhancer] Post-processing: artifact correction")
        result = PostProcessor.process(
            result=result,
            original=upscaled,
            masks=fine_masks,
            intensity=intensity
        )
        if progress_cb: progress_cb(96)

        # === СЛОЙ 5: Финальная постобработка ===
        if stats['needs_sharpen']:
            print(f"[enhancer] Layer 5: Final sharpening (strength={stats['sharpen_strength']:.1f})")
            arr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            blur = cv2.GaussianBlur(arr, (0, 0), 1.0)
            alpha = 1.0 + stats['sharpen_strength'] * 0.15
            beta = -stats['sharpen_strength'] * 0.15
            arr = cv2.addWeighted(arr, alpha, blur, beta, 0)
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            result = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        # === СЛОЙ 5: Глобальное цветовое выравнивание ===
        print("[enhancer] Layer 5: Global color matching")
        try:
            from skimage.exposure import match_histograms
            result_arr = np.array(result)
            upscaled_arr = np.array(upscaled)

            # Глобальный histogram matching с весом 0.4
            matched = match_histograms(result_arr, upscaled_arr, channel_axis=2)
            result_arr = result_arr.astype(np.float32) * 0.6 + matched.astype(np.float32) * 0.4
            result = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
        except ImportError:
            print("[enhancer] skimage not available, skipping global color matching")

        # === СЛОЙ 6: Frequency Separation (сохранение деталей оригинала) ===
        print("[enhancer] Layer 6: Frequency separation")
        from .frequency_separation import adaptive_frequency_separation

        # Создаём маску лица для адаптивной силы деталей
        face_mask = np.zeros((upscaled.size[1], upscaled.size[0]), dtype=np.float32)
        for bbox in face_bboxes:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(upscaled.size[0], x2)
            y2 = min(upscaled.size[1], y2)
            face_mask[y1:y2, x1:x2] = 1.0

        # Размываем маску для плавного перехода
        if face_mask.max() > 0:
            face_mask = cv2.GaussianBlur(face_mask, (51, 51), 15)

        # Применяем frequency separation: лицо 60% деталей, фон 90% деталей
        result = adaptive_frequency_separation(
            original=upscaled,
            enhanced=result,
            face_mask=face_mask if face_mask.max() > 0 else None,
            face_detail_strength=0.6,  # Лицо: больше улучшения, меньше оригинала
            background_detail_strength=0.9,  # Фон: больше оригинала
            blur_radius=3.0
        )

        if progress_cb: progress_cb(100)

        tw, th = result.size
        info_parts = [
            f"{w}x{h} -> {tw}x{th}",
            f"[Landmark Pipeline x{len(faces)}]",
            f"F:{fidelity:.1f}",
            f"I:{int(intensity*100)}%",
            f"Q:{stats['quality_score']:.1f}/10"
        ]

        info = "  ".join(info_parts)
        print("[enhancer] === END ===")
        return result, info

    except Exception as e:
        print(f"[enhancer] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: простой LANCZOS
        if progress_cb: progress_cb(5)
        upscaled = _upscale_script(img, progress_cb)
        if progress_cb: progress_cb(100)

        tw, th = upscaled.size
        info = f"{w}x{h} -> {tw}x{th}  [LANCZOS fallback]"
        print("[enhancer] === END ===")
        return upscaled, info


def _apply_zone_processing_no_faces(
    img: Image.Image,
    masks: dict,
    intensity: float
) -> Image.Image:
    """
    Зональная обработка для изображений без лиц.
    """
    from .zone_processor import ZoneProcessor

    base_arr = np.array(img)
    result = base_arr.astype(np.float32)

    # Обрабатываем фон
    if masks['background'].max() > 0.01:
        bg_processed = ZoneProcessor.process_background(base_arr, intensity)
        bg_mask = masks['background'][:, :, np.newaxis]
        result = result * (1 - bg_mask) + bg_processed.astype(np.float32) * bg_mask

    # Обрабатываем небо
    if masks['sky'].max() > 0.01:
        sky_processed = ZoneProcessor.process_sky(base_arr, intensity)
        sky_mask = masks['sky'][:, :, np.newaxis]
        result = result * (1 - sky_mask) + sky_processed.astype(np.float32) * sky_mask

    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def _apply_zone_processing_with_faces(
    img: Image.Image,
    masks: dict,
    face_bboxes: list,
    intensity: float
) -> Image.Image:
    """
    Зональная обработка с учётом лиц.
    """
    from .zone_processor import ZoneProcessor
    from .segmentor import ImageSegmentor

    base_arr = np.array(img)
    result = base_arr.astype(np.float32)
    w, h = img.size

    # Получаем маску одежды (person минус лица)
    segmentor = ImageSegmentor()
    clothing_mask = segmentor.get_clothing_mask(masks['person'], face_bboxes, (w, h))

    # Обрабатываем одежду
    if clothing_mask.max() > 0.01:
        clothing_processed = ZoneProcessor.process_clothing(base_arr, intensity)
        cloth_mask_3ch = clothing_mask[:, :, np.newaxis]
        result = result * (1 - cloth_mask_3ch) + clothing_processed.astype(np.float32) * cloth_mask_3ch

    # Обрабатываем фон
    if masks['background'].max() > 0.01:
        bg_processed = ZoneProcessor.process_background(base_arr, intensity)
        bg_mask = masks['background'][:, :, np.newaxis]
        result = result * (1 - bg_mask) + bg_processed.astype(np.float32) * bg_mask

    # Обрабатываем небо
    if masks['sky'].max() > 0.01:
        sky_processed = ZoneProcessor.process_sky(base_arr, intensity)
        sky_mask = masks['sky'][:, :, np.newaxis]
        result = result * (1 - sky_mask) + sky_processed.astype(np.float32) * sky_mask

    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)

