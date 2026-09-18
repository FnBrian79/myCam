import os
import pytest
from photos_ingest import (
    compute_file_sha256,
    compute_bytes_sha256,
    get_designated_photo_sources,
    ingest_from_directory
)

def test_compute_bytes_and_file_sha256(tmp_path):
    sample_data = b"mycam_sovereign_photo_data"
    bytes_hash = compute_bytes_sha256(sample_data)

    file_path = tmp_path / "test_img.bin"
    file_path.write_bytes(sample_data)
    file_hash = compute_file_sha256(str(file_path))

    assert bytes_hash == file_hash
    assert len(file_hash) == 64

def test_get_designated_photo_sources(tmp_path):
    custom_dir = str(tmp_path / "my_photos")
    os.makedirs(custom_dir, exist_ok=True)

    config = {
        "storage_dir": str(tmp_path / "captures"),
        "photo_sources": [custom_dir]
    }

    sources = get_designated_photo_sources(config)
    assert custom_dir in sources

def test_ingest_from_directory(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_photos.db")
    monkeypatch.setenv("MYCAM_DB_PATH", db_file)

    src_dir = tmp_path / "photos_source"
    src_dir.mkdir()

    img1 = src_dir / "alice.png"
    img1.write_bytes(b"fake_png_header_123")

    identities_dir = str(tmp_path / "identities")
    os.makedirs(identities_dir, exist_ok=True)

    config = {"storage_dir": str(tmp_path / "captures")}
    count = ingest_from_directory(str(src_dir), identities_dir, limit=10, config=config)

    assert count == 1
    from storage import get_known_identities
    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["name"] == "alice"
