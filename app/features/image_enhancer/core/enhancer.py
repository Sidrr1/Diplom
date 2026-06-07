"""
Главный оркестратор пайплайна улучшения изображений.

Связывает анализ качества, сегментацию, SwinIR-апскейл, CodeFormer для лиц,
зональную обработку и постобработку в единый вызов ``enhance()``.
Параметры ``fidelity`` и ``intensity`` из UI управляют балансом
«похожесть на оригинал / сила эффекта».
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

# Максимальная длинная сторона выходного кадра (fallback LANCZOS)
MAX_OUTPUT_PX = 2560
# Выше ~1.2 Mpx — SwinIR x4 раздувает до 50+ Mpx и рвёт VRAM на fine-seg / CodeFormer
_UPSCALE_X2_MP_THRESHOLD = 1.2
_UPSCALE_X2_LONG_SIDE = 1400

SUPPORTED_EXT = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".webp",
    ".tiff", ".tif", ".gif", ".ico", ".ppm", ".pgm", ".pbm", ".dib"
}


def open_image(path: str) -> Image.Image:
    """Открыть файл изображения; GIF/анимация — только первый кадр, всегда RGB."""
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        img.seek(0)
    return img.convert("RGB")


def _assess_quality(img: Image.Image) -> dict:
    """Быстрая оценка резкости, шума и контраста (используется в fallback-пути)."""
    arr = np.array(img.convert("L"), dtype=np.float32)
    lap = cv2.Laplacian(arr.astype(np.uint8), cv2.CV_64F)
    blur = cv2.GaussianBlur(arr.astype(np.uint8), (5, 5), 0)
    return {
        "sharpness": lap.var(),
        "noise":     np.abs(arr - blur).mean(),
        "contrast":  arr.std(),
        "is_low_res": img.width * img.height < 480 * 360,
    }


def _free_vram():
    """Освободить VRAM между тяжёлыми этапами (SwinIR → сегментация → CodeFormer)."""
    try:
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _choose_upscale_scale(w: int, h: int) -> int:
    """Выбрать масштаб SwinIR: x2 для крупных кадров, x4 для мелких (экономия VRAM)."""
    mp = (w * h) / 1_000_000
    long_side = max(w, h)
    if mp >= _UPSCALE_X2_MP_THRESHOLD or long_side >= _UPSCALE_X2_LONG_SIDE:
        return 2
    return 4


def _upscale_masks(masks: dict, target_size: tuple[int, int]) -> dict:
    """Масштабировать маски сегментации до размера апскейленного кадра (fallback)."""
    tw, th = target_size
    out = {}
    for key, mask in masks.items():
        out[key] = cv2.resize(mask, (tw, th), interpolation=cv2.INTER_LINEAR)
        out[key] = np.clip(out[key], 0, 1).astype(np.float32)
    return out


def _codeformer_fidelity(ui_fidelity: float) -> float:
    """UI fidelity → CodeFormer w (выше = ближе к оригиналу, меньше «пластика»)."""
    return min(1.0, max(0.82, 0.62 + ui_fidelity * 0.38))


def _effect_strength(intensity: float) -> float:
    """Нелинейная кривая силы эффектов — даже при 100% UI не давить на полную."""
    return float(np.clip(intensity ** 1.35 * 0.72, 0.0, 1.0))


def _blend_with_upscaled(
    result: Image.Image,
    upscaled: Image.Image,
    fidelity: float,
    intensity: float,
) -> Image.Image:
    """Смешать с чистым SwinIR — убирает липовую генерацию."""
    effect = _effect_strength(intensity)
    keep = 0.32 + 0.42 * fidelity + 0.18 * (1.0 - effect)  # доля чистого SwinIR в финале
    keep = float(np.clip(keep, 0.38, 0.82))
    r = np.array(result, dtype=np.float32)
    u = np.array(upscaled, dtype=np.float32)
    if r.shape != u.shape:
        u = cv2.resize(u, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_LANCZOS4)
    out = u * keep + r * (1.0 - keep)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def _upscale_script(img: Image.Image, progress_cb=None) -> Image.Image:
    """Fallback при сбое пайплайна: апскейл LANCZOS до MAX_OUTPUT_PX."""
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
    Семантически осведомлённый пайплайн улучшения изображения.

    Слой 1: Грубая сегментация и детекция лиц (до апскейла)
    Слой 2: SwinIR x2/x4 апскейл
    Слой 3: Точная сегментация и лица (после апскейла)
    Слой 3.5: Landmark-анализ (MediaPipe)
    Слой 4: Зональная обработка (CodeFormer, landmark-зоны, фон/одежда)
    Слои 5–6: Sharpen, frequency separation, финальный blend с SwinIR

    Args:
        img: входное изображение (PIL RGB)
        fidelity: похожесть на оригинал для CodeFormer (0.0–1.0)
        intensity: сила эффектов из UI (0.0–1.0)
        progress_cb: callback прогресса (0–100)

    Returns:
        (улучшенное изображение, текстовая сводка для UI)
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
        effect = _effect_strength(intensity)       # нелинейная сила эффектов [0..1]
        cf_fidelity = _codeformer_fidelity(fidelity)  # w CodeFormer: выше → ближе к оригиналу

        if stats['needs_denoise'] and stats['quality_score'] < 6.0:
            denoise_h = min(stats['denoise_strength'], 8 if stats['quality_score'] < 5.0 else 12)
            print(f"[enhancer] Applying light denoise (strength={denoise_h})")
            arr = cv2.cvtColor(np.array(preprocessed), cv2.COLOR_RGB2BGR)
            arr = cv2.fastNlMeansDenoisingColored(
                arr, None,
                h=denoise_h,
                hColor=denoise_h,
                templateWindowSize=7,
                searchWindowSize=21
            )
            preprocessed = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        if stats['needs_contrast_boost'] and stats['quality_score'] >= 5.0:
            clahe_clip = min(stats['clahe_clip'], 1.6)
            print(f"[enhancer] Applying contrast boost (CLAHE={clahe_clip:.1f})")
            arr = cv2.cvtColor(np.array(preprocessed), cv2.COLOR_RGB2BGR)
            lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
            l = clahe.apply(l)
            arr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
            preprocessed = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        if progress_cb: progress_cb(20)

        # === СЛОЙ 2: SwinIR апскейл (x2 на крупных кадрах) ===
        upscale_scale = _choose_upscale_scale(preprocessed.width, preprocessed.height)
        print(f"[enhancer] Layer 2: SwinIR x{upscale_scale} upscale")
        swinir = manager.get_swinir_upscaler(scale=upscale_scale)
        upscaled = swinir.upscale(preprocessed, tile_size=512)
        print(f"[enhancer] Layer 2: {w}x{h} -> {upscaled.size[0]}x{upscaled.size[1]}")
        if progress_cb: progress_cb(45)
        _free_vram()

        # === СЛОЙ 3: Точная сегментация (после апскейла) ===
        print("[enhancer] Layer 3: Fine segmentation")
        try:
            fine_masks = segmentor.segment(upscaled)
        except Exception as seg_err:
            print(f"[enhancer] Fine segmentation failed ({seg_err}), using coarse masks")
            _free_vram()
            fine_masks = _upscale_masks(coarse_masks, upscaled.size)
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
            print("[enhancer] No faces detected, light zone processing")
            result = upscaled
            if effect >= 0.25:
                result = _apply_zone_processing_no_faces(upscaled, fine_masks, effect * 0.35)

            if effect >= 0.3:
                print("[enhancer] Applying frequency separation (no faces)")
                from .frequency_separation import frequency_separation
                result = frequency_separation(
                    original=upscaled,
                    enhanced=result,
                    blur_radius=3.0,
                    detail_strength=0.92,
                )

            result = _blend_with_upscaled(result, upscaled, fidelity, intensity)

            if progress_cb: progress_cb(100)

            tw, th = result.size
            info = (
                f"{w}x{h} -> {tw}x{th}  [Natural · SwinIR×{upscale_scale} · лиц:0]  "
                f"Q:{stats['quality_score']:.1f}/10"
            )
            print("[enhancer] === END ===")
            return result, info

        # === СЛОЙ 4: Зональная обработка ===
        print("[enhancer] Layer 4: Zone processing")

        # 4a: Региональная обработка лиц (CodeFormer + мягкие детали)
        processor = RegionalProcessor(manager)
        result = processor.process_regions(
            original=img,
            upscaled=upscaled,
            face_bboxes=face_bboxes,
            fidelity=cf_fidelity,
            effect_strength=effect,
        )
        if progress_cb: progress_cb(70)

        # 4b: Landmark-зоны — только при высокой интенсивности (иначе пятна на коже)
        if effect >= 0.55:
            print("[enhancer] Layer 4b: Landmark zones (light)")
            from .landmark_processor import LandmarkProcessor
            landmark_proc = LandmarkProcessor()
            landmark_intensity = effect * 0.35
            for i, (face_bbox, landmarks) in enumerate(zip(face_bboxes, face_landmarks)):
                if landmarks['zones']:
                    print(f"[enhancer] Processing {len(landmarks['zones'])} zones for face {i+1}")
                    result = landmark_proc.process_face_zones(
                        result,
                        landmarks,
                        face_bbox,
                        intensity=landmark_intensity,
                    )
        else:
            print("[enhancer] Layer 4b: Skipped (low intensity — natural mode)")

        if progress_cb: progress_cb(85)

        # 4c: Фон/одежда — только лёгкая обработка
        if effect >= 0.25:
            result = _apply_zone_processing_with_faces(
                result, fine_masks, face_bboxes, effect * 0.35
            )
        else:
            print("[enhancer] Layer 4c: Skipped (natural mode)")

        if progress_cb: progress_cb(90)

        # === ПОСТОБРАБОТКА: только мягкая коррекция ===
        if effect >= 0.2:
            print("[enhancer] Post-processing: light artifact correction")
            result = PostProcessor.process(
                result=result,
                original=upscaled,
                masks=fine_masks,
                intensity=effect * 0.4,
                tone_map=effect >= 0.65,
            )
        if progress_cb: progress_cb(96)

        # === СЛОЙ 5: Лёгкий sharpen только при очень мягком входе ===
        if stats['needs_sharpen'] and stats['quality_score'] < 4.0 and effect >= 0.5:
            sharpen_amt = stats['sharpen_strength'] * effect * 0.08
            print(f"[enhancer] Layer 5: Light sharpening (strength={sharpen_amt:.2f})")
            arr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            blur = cv2.GaussianBlur(arr, (0, 0), 1.0)
            alpha = 1.0 + sharpen_amt
            beta = -sharpen_amt
            arr = cv2.addWeighted(arr, alpha, blur, beta, 0)
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            result = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

        # === СЛОЙ 6: Frequency separation — больше оригинала, меньше артефактов ===
        if effect >= 0.3:
            print("[enhancer] Layer 6: Frequency separation (light)")
            from .frequency_separation import adaptive_frequency_separation

            face_mask = np.zeros((upscaled.size[1], upscaled.size[0]), dtype=np.float32)
            for bbox in face_bboxes:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(upscaled.size[0], x2)
                y2 = min(upscaled.size[1], y2)
                face_mask[y1:y2, x1:x2] = 1.0  # бинарная маска всех лиц для frequency separation

            if face_mask.max() > 0:
                face_mask = cv2.GaussianBlur(face_mask, (51, 51), 15)  # мягкие границы зоны лица

            result = adaptive_frequency_separation(
                original=upscaled,
                enhanced=result,
                face_mask=face_mask if face_mask.max() > 0 else None,
                face_detail_strength=0.88,
                background_detail_strength=0.94,
                blur_radius=3.0,
            )

        # === Финальный blend с чистым SwinIR ===
        print(f"[enhancer] Natural blend (CF w={cf_fidelity:.2f}, effect={effect:.2f})")
        result = _blend_with_upscaled(result, upscaled, fidelity, intensity)

        if progress_cb: progress_cb(100)

        tw, th = result.size
        info_parts = [
            f"{w}x{h} -> {tw}x{th}",
            f"[Natural · SwinIR×{upscale_scale} · лиц:{len(faces)}]",
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
        _free_vram()

        # Если SwinIR уже отработал — отдаём апскейл, а не исходник
        partial = locals().get("upscaled")
        if partial is not None and partial.size != img.size:
            if progress_cb: progress_cb(100)
            tw, th = partial.size
            info = (
                f"{w}x{h} -> {tw}x{th}  [SwinIR partial — лица/зоны пропущены: VRAM]"
            )
            print("[enhancer] === END (partial) ===")
            return partial, info

        if progress_cb: progress_cb(5)
        upscaled_fb = _upscale_script(img, progress_cb)
        if progress_cb: progress_cb(100)

        tw, th = upscaled_fb.size
        info = f"{w}x{h} -> {tw}x{th}  [LANCZOS fallback]"
        print("[enhancer] === END ===")
        return upscaled_fb, info


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

