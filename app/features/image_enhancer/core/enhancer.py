import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

MAX_OUTPUT_PX = 2560

_MODEL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "..", "bin", "RealESRGAN_x4plus.pth"
))

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


def _esrgan_available() -> bool:
    return os.path.exists(_MODEL_PATH)


def _upscale_esrgan(img: Image.Image, progress_cb=None) -> Image.Image:
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=4)
    upsampler = RealESRGANer(
        scale=4,
        model_path=_MODEL_PATH,
        model=model,
        tile=256,          # тайлинг — экономит память
        tile_pad=10,
        pre_pad=0,
        half=False
    )
    if progress_cb: progress_cb(30)

    arr = np.array(img)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    out_bgr, _ = upsampler.enhance(bgr, outscale=4)
    if progress_cb: progress_cb(75)

    return Image.fromarray(cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB))


def _upscale_script(img: Image.Image, progress_cb=None) -> Image.Image:
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


def _postprocess(arr: np.ndarray, metrics: dict, aggressive: bool) -> np.ndarray:
    # Лёгкий шумодав — не ломает детали после ESRGAN
    h_val = 4 if not aggressive else 7
    arr = cv2.fastNlMeansDenoisingColored(
        arr, None, h=h_val, hColor=h_val,
        templateWindowSize=7, searchWindowSize=15
    )
    # Unsharp mask только если реально размытое
    if metrics["sharpness"] < 60:
        blur_a = cv2.GaussianBlur(arr, (0, 0), 1.2)
        arr = cv2.addWeighted(arr, 1.3, blur_a, -0.3, 0)
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    # CLAHE мягко
    clip = 1.5 if aggressive else 1.0
    lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    l = clahe.apply(l)
    arr = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    return arr


def enhance(img: Image.Image, use_esrgan: bool = True,
            progress_cb=None) -> tuple[Image.Image, str]:
    w, h = img.size
    metrics = _assess_quality(img)
    aggressive = (metrics["sharpness"] < 80 or
                  metrics["contrast"] < 35 or
                  metrics["is_low_res"])
    method = "script"

    if progress_cb: progress_cb(5)

    if use_esrgan and _esrgan_available():
        try:
            upscaled = _upscale_esrgan(img, progress_cb)
            method = "Real-ESRGAN x4"
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[enhancer] ESRGAN failed: {e}, fallback to script")
            upscaled = _upscale_script(img, progress_cb)
    else:
        upscaled = _upscale_script(img, progress_cb)

    arr = cv2.cvtColor(np.array(upscaled), cv2.COLOR_RGB2BGR)
    arr = _postprocess(arr, metrics, aggressive)
    if progress_cb: progress_cb(92)

    result = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

    if aggressive and metrics["contrast"] < 30:
        result = ImageEnhance.Contrast(result).enhance(1.15)

    if progress_cb: progress_cb(100)

    tw2, th2 = result.size
    info = (f"{w}×{h} → {tw2}×{th2}  [{method}]  "
            f"резкость:{metrics['sharpness']:.0f}  "
            f"контраст:{metrics['contrast']:.0f}")
    return result, info