import os
import pytest
from PIL import Image
from video import compile_frames_to_animation

def test_compile_frames_to_animation(tmp_path):
    event_folder = tmp_path / "event_1"
    event_folder.mkdir()

    # Create dummy PNG frames
    for i in range(3):
        img = Image.new("RGB", (100, 100), color=(i * 50, 100, 150))
        img.save(event_folder / f"frame_{i:04d}.png")

    anim_path = compile_frames_to_animation(str(event_folder), output_format="gif", fps=5)
    assert anim_path is not None
    assert os.path.exists(anim_path)

def test_compile_frames_empty_dir(tmp_path):
    empty_folder = tmp_path / "empty"
    empty_folder.mkdir()
    res = compile_frames_to_animation(str(empty_folder))
    assert res is None
