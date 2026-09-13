import os
import zipfile
import tempfile
import pytest
from PIL import Image

from recorder import capture_screenshot, capture_sequence
from video import compile_frames_to_animation
from photos_ingest import (
    get_designated_photo_sources,
    ingest_from_directory,
    ingest_from_takeout_zip,
    run_photo_ingest_pipeline
)

def test_video_compile_animation(tmp_path):
    event_folder = tmp_path / "event_1"
    event_folder.mkdir()

    # Create 3 test frame PNGs
    for i in range(3):
        img = Image.new("RGB", (100, 100), color=(i * 50, 100, 150))
        img.save(event_folder / f"frame_{i:04d}.png")

    anim_path = compile_frames_to_animation(str(event_folder), output_format="gif", fps=5)
    assert anim_path is not None
    assert os.path.exists(anim_path)

def test_photos_ingest_sources(tmp_path):
    config = {"photo_sources": [str(tmp_path)]}
    sources = get_designated_photo_sources(config)
    assert str(tmp_path) in sources

def test_photos_ingest_from_directory(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_ingest.db")
    monkeypatch.setenv("MYCAM_DB_PATH", test_db)

    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    img = Image.new("RGB", (50, 50), color="blue")
    img.save(photo_dir / "test_person.jpg")

    identities_dir = str(tmp_path / "identities")
    os.makedirs(identities_dir, exist_ok=True)

    count = ingest_from_directory(str(photo_dir), identities_dir, limit=10)
    assert count == 1

def test_photos_ingest_from_takeout_zip(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_takeout.db")
    monkeypatch.setenv("MYCAM_DB_PATH", test_db)

    zip_path = tmp_path / "takeout.zip"
    img_data = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img = Image.new("RGB", (50, 50), color="red")
    img.save(img_data.name)

    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(img_data.name, arcname="Takeout/Google Photos/Profile Pictures/user.jpg")
    os.unlink(img_data.name)

    identities_dir = str(tmp_path / "identities")
    os.makedirs(identities_dir, exist_ok=True)

    count = ingest_from_takeout_zip(str(zip_path), identities_dir, limit=10)
    assert count == 1
