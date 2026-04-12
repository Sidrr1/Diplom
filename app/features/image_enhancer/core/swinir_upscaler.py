"""
SwinIR upscaler для общего улучшения изображения.
"""
import os
import cv2
import numpy as np
import torch
from PIL import Image


class SwinIRUpscaler:
    def __init__(self, model_path: str = None, scale: int = 4):
        """
        Args:
            model_path: путь к .pth модели SwinIR
            scale: масштаб апскейла (2 или 4)
        """
        if model_path is None:
            bin_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
                "bin"
            )
            if scale == 4:
                model_path = os.path.join(bin_dir, "003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth")
            else:
                model_path = os.path.join(bin_dir, "001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth")

        self.model_path = model_path
        self.scale = scale
        self.net = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        """Lazy load модели."""
        if self.net is not None:
            return

        try:
            from basicsr.archs.swinir_arch import SwinIR

            # Параметры для Real-World GAN x4
            if self.scale == 4:
                self.net = SwinIR(
                    upscale=4,
                    in_chans=3,
                    img_size=64,
                    window_size=8,
                    img_range=1.0,
                    depths=[6, 6, 6, 6, 6, 6, 6, 6, 6],
                    embed_dim=240,
                    num_heads=[8, 8, 8, 8, 8, 8, 8, 8, 8],
                    mlp_ratio=2,
                    upsampler='nearest+conv',
                    resi_connection='3conv'
                )
            else:  # scale == 2
                self.net = SwinIR(
                    upscale=2,
                    in_chans=3,
                    img_size=64,
                    window_size=8,
                    img_range=1.0,
                    depths=[6, 6, 6, 6, 6, 6],
                    embed_dim=180,
                    num_heads=[6, 6, 6, 6, 6, 6],
                    mlp_ratio=2,
                    upsampler='pixelshuffle',
                    resi_connection='1conv'
                )

            # Загружаем веса
            checkpoint = torch.load(self.model_path, map_location=self.device)
            if 'params_ema' in checkpoint:
                self.net.load_state_dict(checkpoint['params_ema'], strict=True)
            elif 'params' in checkpoint:
                self.net.load_state_dict(checkpoint['params'], strict=True)
            else:
                self.net.load_state_dict(checkpoint, strict=True)

            self.net.eval()
            self.net = self.net.to(self.device)
            print(f"[swinir] Loaded SwinIR x{self.scale} from {self.model_path}")
        except Exception as e:
            print(f"[swinir] Failed to load SwinIR: {e}")
            raise

    def upscale(self, img: Image.Image, tile_size: int = 512) -> Image.Image:
        """
        Апскейл изображения через SwinIR с тайлингом.

        Args:
            img: PIL Image
            tile_size: размер тайла для обработки больших изображений

        Returns:
            улучшенное изображение (PIL Image)
        """
        self.load()

        # Конвертируем PIL -> numpy BGR
        arr = np.array(img)
        arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Нормализация [0, 1]
        arr_bgr = arr_bgr.astype(np.float32) / 255.0

        # BGR -> RGB -> Tensor
        arr_rgb = cv2.cvtColor(arr_bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(arr_rgb).permute(2, 0, 1).unsqueeze(0).to(self.device)

        # Паддинг до размера кратного window_size * scale
        _, _, h_old, w_old = tensor.shape
        window_size = 8
        mod_pad_h = (window_size - h_old % window_size) % window_size
        mod_pad_w = (window_size - w_old % window_size) % window_size

        tensor = torch.nn.functional.pad(tensor, (0, mod_pad_w, 0, mod_pad_h), 'reflect')

        # Inference с тайлингом если изображение большое
        _, _, h, w = tensor.shape
        if h > tile_size or w > tile_size:
            output = self._tile_process(tensor, tile_size)
        else:
            with torch.no_grad():
                output = self.net(tensor)

        # Обрезаем паддинг
        _, _, h_new, w_new = output.shape
        output = output[:, :, :h_old * self.scale, :w_old * self.scale]

        # Tensor -> numpy
        output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = np.clip(output * 255.0, 0, 255).astype(np.uint8)

        # RGB -> PIL
        return Image.fromarray(output)

    def _tile_process(self, img_tensor: torch.Tensor, tile_size: int) -> torch.Tensor:
        """Обработка большого изображения по тайлам."""
        b, c, h, w = img_tensor.shape
        tile_overlap = 32
        stride = tile_size - tile_overlap

        output = torch.zeros(
            (b, c, h * self.scale, w * self.scale),
            dtype=img_tensor.dtype,
            device=self.device
        )
        count = torch.zeros_like(output)

        for y in range(0, h, stride):
            for x in range(0, w, stride):
                y_end = min(y + tile_size, h)
                x_end = min(x + tile_size, w)

                tile = img_tensor[:, :, y:y_end, x:x_end]

                with torch.no_grad():
                    tile_out = self.net(tile)

                out_y = y * self.scale
                out_x = x * self.scale
                out_y_end = y_end * self.scale
                out_x_end = x_end * self.scale

                output[:, :, out_y:out_y_end, out_x:out_x_end] += tile_out
                count[:, :, out_y:out_y_end, out_x:out_x_end] += 1

        output = output / count
        return output

    def unload(self):
        """Выгрузка модели из памяти."""
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[swinir] Unloaded SwinIR")
