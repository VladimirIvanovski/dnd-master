from pathlib import Path

import pytest

from app.core.config import get_settings
from app.visual.provider import (
    MockImageProvider,
    SdTurboCpuProvider,
    get_image_provider,
    reset_image_provider,
)


def test_default_test_provider_is_mock():
    reset_image_provider()
    provider = get_image_provider()
    assert provider.kind == "mock"
    img = provider.generate("a quiet tavern", width=64, height=64)
    assert img.width == 64
    assert img.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_sd_turbo_unavailable_without_weights():
    missing = SdTurboCpuProvider("storage/models/missing-sd-turbo")
    assert missing.is_available() is False
    reset_image_provider()
    assert get_image_provider().kind == "mock"


@pytest.mark.live
def test_sd_turbo_generates_real_png():
    settings = get_settings()
    path = Path(settings.image_model_path)
    provider = SdTurboCpuProvider(str(path), settings.image_device)
    if not provider.is_available():
        pytest.skip(f"SD-Turbo weights missing at {path}")
    mock = MockImageProvider().generate("a ruined watchtower at dusk", width=64, height=64)
    real = provider.generate("a ruined watchtower at dusk", width=64, height=64, steps=1)
    assert real.data[:8] == b"\x89PNG\r\n\x1a\n"
    assert real.width >= 64 and real.height >= 64
    assert real.data != mock.data
