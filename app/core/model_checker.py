"""
Проверка наличия ML-моделей для модуля улучшения изображений EdgeTools.

Сканирует папку bin/ и предупреждает пользователя о недостающих .pth/.onnx.
"""
import os
from typing import Dict, List


def get_bin_dir() -> str:
    """
    Получить путь к папке bin/ в корне проекта.

    Returns:
        Абсолютный путь к каталогу с весами моделей.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    bin_dir = os.path.join(project_root, "bin")
    return bin_dir


def check_models() -> Dict[str, bool]:
    """
    Проверить наличие всех обязательных моделей.

    Returns:
        Словарь {имя_файла: существует_ли}.
    """
    bin_dir = get_bin_dir()

    models = {
        'detection_Resnet50_Final.pth': os.path.join(bin_dir, 'detection_Resnet50_Final.pth'),
        'codeformer.pth': os.path.join(bin_dir, 'codeformer.pth'),
        'parsing_parsenet.pth': os.path.join(bin_dir, 'parsing_parsenet.pth'),
        '003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth': os.path.join(bin_dir, '003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth'),
        '001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth': os.path.join(bin_dir, '001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth'),
        'w600k_r50.onnx': os.path.join(bin_dir, 'w600k_r50.onnx'),
    }

    return {name: os.path.exists(path) for name, path in models.items()}


def get_missing_models() -> List[str]:
    """
    Получить список отсутствующих моделей.

    Returns:
        Имена файлов, которых нет в bin/.
    """
    models_status = check_models()
    return [name for name, exists in models_status.items() if not exists]


def get_download_links() -> Dict[str, str]:
    """
    Получить ссылки для скачивания моделей.

    Returns:
        Словарь {имя_файла: URL релиза}.
    """
    return {
        'detection_Resnet50_Final.pth': 'https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth',
        'codeformer.pth': 'https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth',
        'parsing_parsenet.pth': 'https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/parsing_parsenet.pth',
        '003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth': 'https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth',
        '001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth': 'https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth',
        'w600k_r50.onnx': 'https://github.com/deepinsight/insightface/releases/download/v0.7/w600k_r50.onnx',
    }


def show_missing_models_dialog(missing: List[str]):
    """
    Показать диалог с информацией об отсутствующих моделях.

    Args:
        missing: список имён файлов, которых нет в bin/.
    """
    from app.core.logger import log_error

    bin_dir = get_bin_dir()
    download_links = get_download_links()

    message = f"Отсутствуют файлы моделей ({len(missing)} из 6):\n\n"

    for model_name in missing:
        url = download_links.get(model_name, 'N/A')
        message += f"• {model_name}\n  {url}\n\n"

    message += f"\nСкачайте файлы и поместите их в папку:\n{bin_dir}\n\n"
    message += "Без моделей функция улучшения изображений работать не будет."

    log_error(
        "Модели не найдены",
        message,
        None
    )

    print(f"[model_checker] Missing models: {', '.join(missing)}")
    print(f"[model_checker] Bin directory: {bin_dir}")


def check_and_warn():
    """
    Проверить модели и показать предупреждение при отсутствии файлов.

    Returns:
        True, если все модели на месте; False при пропусках.
    """
    missing = get_missing_models()

    if missing:
        show_missing_models_dialog(missing)
        return False

    print(f"[model_checker] All models found ✓")
    return True
