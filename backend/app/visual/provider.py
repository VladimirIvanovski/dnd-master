from __future__ import annotations

import hashlib
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    data: bytes
    mime_type: str
    width: int
    height: int


class ImageGenerationProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def generate(self, prompt: str, *, width: int, height: int, steps: int = 12) -> GeneratedImage: ...

    def generate_from_reference(
        self, prompt: str, reference: bytes, *, width: int, height: int, steps: int = 12
    ) -> GeneratedImage:
        return self.generate(prompt, width=width, height=height, steps=steps)


class MockImageProvider(ImageGenerationProvider):
    """Deterministic placeholder PNGs — never blocks on a real model."""

    kind = "mock"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, *, width: int, height: int, steps: int = 12) -> GeneratedImage:
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            png = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
                b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            return GeneratedImage(data=png, mime_type="image/png", width=1, height=1)

        digest = hashlib.sha256(prompt.encode()).digest()
        color = (40 + digest[0] % 80, 50 + digest[1] % 90, 70 + digest[2] % 100)
        accent = (180 + digest[3] % 60, 140 + digest[4] % 50, 60 + digest[5] % 40)
        img = Image.new("RGB", (width, height), color)
        draw = ImageDraw.Draw(img)
        margin = max(8, width // 16)
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=accent,
            width=max(2, width // 64),
        )
        label = (prompt[:48] + "…") if len(prompt) > 48 else prompt
        draw.text((margin + 6, margin + 6), label, fill=(230, 230, 230))
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return GeneratedImage(data=buf.getvalue(), mime_type="image/png", width=width, height=height)


def _snap_dim(value: int, minimum: int = 64) -> int:
    return max(minimum, (int(value) // 8) * 8)


class SdTurboCpuProvider(ImageGenerationProvider):
    """Local SD-Turbo via Diffusers, CPU inference, variable resolutions."""

    kind = "sd-turbo"

    def __init__(self, model_path: str, device: str = "cpu"):
        self.model_path = str(Path(model_path))
        self.device = device
        self._pipe = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        root = Path(self.model_path)
        return root.is_dir() and any(root.iterdir())

    def _ensure_pipeline(self) -> None:
        if self._pipe is not None:
            return
        import torch
        from diffusers import AutoPipelineForText2Image

        logger.info("Loading SD-Turbo from %s (%s)", self.model_path, self.device)
        pipe = AutoPipelineForText2Image.from_pretrained(
            self.model_path,
            torch_dtype=torch.float32,
            local_files_only=True,
        )
        pipe.to(self.device)
        pipe.set_progress_bar_config(disable=True)
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing()
        self._pipe = pipe

    def generate(self, prompt: str, *, width: int, height: int, steps: int = 1) -> GeneratedImage:
        from PIL import Image

        w, h = _snap_dim(width), _snap_dim(height)
        # SD-Turbo is tuned around 512; tiny icons look better downscaled.
        gen_w, gen_h = w, h
        if w < 256 or h < 256:
            gen_w = max(w, 256)
            gen_h = max(h, 256)
            gen_w, gen_h = _snap_dim(gen_w), _snap_dim(gen_h)

        steps = max(1, min(int(steps or 1), 4))
        with self._lock:
            self._ensure_pipeline()
            assert self._pipe is not None
            result = self._pipe(
                prompt,
                num_inference_steps=steps,
                guidance_scale=0.0,
                width=gen_w,
                height=gen_h,
            )
            image: Image.Image = result.images[0]

        if image.size != (w, h):
            image = image.resize((w, h), Image.Resampling.LANCZOS)
        buf = BytesIO()
        image.save(buf, format="PNG", optimize=True)
        return GeneratedImage(data=buf.getvalue(), mime_type="image/png", width=w, height=h)


_provider_singleton: ImageGenerationProvider | None = None
_provider_lock = threading.Lock()


def get_image_provider() -> ImageGenerationProvider:
    """Return a process-wide provider so the model stays loaded in RAM."""
    global _provider_singleton
    with _provider_lock:
        if _provider_singleton is not None:
            return _provider_singleton
        settings = get_settings()
        model = (settings.image_model or "mock").strip().lower()
        if not settings.image_generation_enabled or model in {"mock", "placeholder"}:
            _provider_singleton = MockImageProvider()
            return _provider_singleton
        if model in {"sd-turbo", "stabilityai/sd-turbo", "sdturbo"}:
            provider = SdTurboCpuProvider(settings.image_model_path, settings.image_device)
            if not provider.is_available():
                logger.warning(
                    "SD-Turbo not found at %s — run scripts/download_sd_turbo.py; using mock",
                    settings.image_model_path,
                )
                _provider_singleton = MockImageProvider()
            else:
                _provider_singleton = provider
            return _provider_singleton
        logger.warning("Unknown IMAGE_MODEL=%s; using mock", settings.image_model)
        _provider_singleton = MockImageProvider()
        return _provider_singleton


def reset_image_provider() -> None:
    """Test helper / config reload."""
    global _provider_singleton
    with _provider_lock:
        _provider_singleton = None
