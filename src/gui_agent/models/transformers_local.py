from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from pathlib import Path
from typing import Any

from .base import ModelResponse


class TransformersVisionModel:
    """本地模型后端"""

    def __init__(
        self,
        model_path: str | Path,
        *,
        device_map: str = "auto",
        dtype: str = "auto",
        max_new_tokens: int = 512,
        trust_remote_code: bool = False,
        load_in_4bit: bool = False,
        compute_dtype: str = "bfloat16",
        max_image_pixels: int | None = None,
    ) -> None:
        self.model_path = str(model_path)
        self.device_map = device_map
        self.dtype = dtype
        self.max_new_tokens = max_new_tokens
        self.trust_remote_code = trust_remote_code
        self.load_in_4bit = load_in_4bit
        self.compute_dtype = compute_dtype
        self.max_image_pixels = max_image_pixels
        self._model: Any = None
        self._processor: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        # 延迟加载模型
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model_kwargs: dict[str, Any] = {
            "device_map": self.device_map,
            "torch_dtype": self.dtype,
            "trust_remote_code": self.trust_remote_code,
        }
        if self.load_in_4bit:
            # 降低显存占用
            import torch
            from transformers import BitsAndBytesConfig

            try:
                compute_dtype = getattr(torch, self.compute_dtype)
            except AttributeError as error:
                raise ValueError(f"Unsupported compute dtype: {self.compute_dtype}") from error
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            )

        self._processor = AutoProcessor.from_pretrained(
            self.model_path, trust_remote_code=self.trust_remote_code
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_path,
            **model_kwargs,
        )

    def generate(
        self,
        prompt: str,
        images: Sequence[str | Path] = (),
        *,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        self._load()
        from PIL import Image

        content: list[dict[str, Any]] = []
        loaded_images = []
        for image in images:
            loaded = Image.open(image).convert("RGB")
            if self.max_image_pixels and loaded.width * loaded.height > self.max_image_pixels:
                # 等比缩放图片
                scale = sqrt(self.max_image_pixels / (loaded.width * loaded.height))
                loaded = loaded.resize(
                    (max(1, round(loaded.width * scale)), max(1, round(loaded.height * scale)))
                )
            loaded_images.append(loaded)
            content.append({"type": "image", "image": loaded})
        content.append({"type": "text", "text": prompt})
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        rendered = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(text=[rendered], images=loaded_images or None, return_tensors="pt")
        device = next(self._model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        output = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        prompt_length = inputs["input_ids"].shape[1]
        text = self._processor.batch_decode(output[:, prompt_length:], skip_special_tokens=True)[0]
        return ModelResponse(text.strip(), self.model_path)
