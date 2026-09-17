import os
import pytest
from unittest.mock import patch
from PIL import Image
from recorder import grab_screen, capture_screenshot, capture_sequence

def test_grab_screen_fallback():
    with patch("PIL.ImageGrab.grab", side_effect=Exception("No display")):
        img = grab_screen()
        assert isinstance(img, Image.Image)
        assert img.size == (1920, 1080)

def test_capture_screenshot(tmp_path):
    config = {"storage_dir": str(tmp_path)}
    filepath = capture_screenshot(config, title="Test Snapshot")
    assert filepath is not None
    assert os.path.exists(filepath)
    assert filepath.endswith(".png")

def test_capture_sequence(tmp_path):
    config = {"storage_dir": str(tmp_path)}
    files = capture_sequence(config, duration_sec=1, fps=2, title="Test Sequence")
    assert len(files) >= 2
    for f in files:
        assert os.path.exists(f)
