import os
import cv2
import numpy as np
import torch
from PIL import Image


class FaceEnhancer:
    def __init__(self, model_path: str = None, parsing_path: str = None):
        if model_path is None:
            model_path = os.path.join("bin", "codeformer.pth")
        if parsing_path is None:
            parsing_path = os.path.join("bin", "parsing_parsenet.pth")

        self.model_path   = model_path
        self.parsing_path = parsing_path
        self.net          = None
        self.device       = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        if self.net is not None:
            return
        from basicsr.archs.codeformer_arch import CodeFormer

        self.net = CodeFormer(
            dim_embd=512,
            codebook_size=1024,
            n_head=8,
            n_layers=9,
            connect_list=["32", "64", "128", "256"]
        ).to(self.device)

        checkpoint = torch.load(
            self.model_path,
            map_location=self.device,
            weights_only=False
        )
        state = checkpoint.get("params_ema", checkpoint)
        self.net.load_state_dict(state, strict=True)
        self.net.eval()
        print(f"[face_enhancer] Loaded CodeFormer from {self.model_path}")

    def enhance_face(self, face_img: Image.Image, fidelity: float = 0.7) -> Image.Image:
        self.load()

        orig_w, orig_h = face_img.size

        # PIL RGB -> numpy BGR
        arr = cv2.cvtColor(np.array(face_img), cv2.COLOR_RGB2BGR)

        # Resize до 512x512
        arr = cv2.resize(arr, (512, 512), interpolation=cv2.INTER_LINEAR)

        # BGR -> RGB, нормализация в [-1, 1]
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        arr = (arr - 0.5) / 0.5  # [0,1] -> [-1,1]

        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            try:
                # Пробуем с adain
                out = self.net(tensor, w=fidelity, adain=True)
            except TypeError:
                try:
                    # Без adain
                    out = self.net(tensor, w=fidelity)
                except TypeError:
                    # Только тензор
                    out = self.net(tensor)

        # Извлекаем тензор результата
        if isinstance(out, (list, tuple)):
            out = out[0]

        # Tensor -> numpy, денормализация из [-1,1] -> [0,255]
        out = out.squeeze(0).permute(1, 2, 0).cpu().numpy()
        out = np.clip((out * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)

        # Resize обратно
        out = cv2.resize(out, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        return Image.fromarray(out)  # уже RGB

    def enhance_faces_batch(self, face_imgs: list, fidelity: float = 0.7) -> list:
        """Обработка нескольких лиц одним батчем."""
        self.load()

        if not face_imgs:
            return []

        # Подготовка батча
        batch_tensors = []
        orig_sizes = []

        for face_img in face_imgs:
            orig_sizes.append(face_img.size)
            arr = cv2.cvtColor(np.array(face_img), cv2.COLOR_RGB2BGR)
            arr = cv2.resize(arr, (512, 512), interpolation=cv2.INTER_LINEAR)
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            arr = (arr - 0.5) / 0.5
            tensor = torch.from_numpy(arr).permute(2, 0, 1)
            batch_tensors.append(tensor)

        batch = torch.stack(batch_tensors).to(self.device)

        # Inference
        with torch.no_grad():
            try:
                out = self.net(batch, w=fidelity, adain=True)
            except TypeError:
                try:
                    out = self.net(batch, w=fidelity)
                except TypeError:
                    out = self.net(batch)

        if isinstance(out, (list, tuple)):
            out = out[0]

        # Конвертация обратно
        results = []
        for i, (orig_w, orig_h) in enumerate(orig_sizes):
            face_out = out[i].permute(1, 2, 0).cpu().numpy()
            face_out = np.clip((face_out * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
            face_out = cv2.resize(face_out, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            results.append(Image.fromarray(face_out))

        return results

    def unload(self):
        if self.net is not None:
            del self.net
            self.net = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[face_enhancer] Unloaded CodeFormer")