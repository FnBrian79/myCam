import os
import sys
import json
import tempfile
import pytest
import sqlite3
import urllib.request
import threading
import time
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault_crypto import encrypt_payload, decrypt_payload, compute_sha256, get_or_create_key
from storage import (
    init_sqlite_ledger, log_event, load_events,
    insert_known_identity, get_known_identities,
    update_training_label, get_storage_dir, get_db_paths
)
from cleon_gate import evaluate_cleon_trip, CleonDynastyGate
from alexa_bridge import get_local_ip, trigger_alexa_alert, CURRENT_STATE
from photos_ingest import compute_file_sha256, ingest_from_directory, compute_bytes_sha256
from video import compile_frames_to_animation


@pytest.fixture
def temp_env(tmp_path):
    """Sets up a clean temporary environment for testing storage & config."""
    db_file = str(tmp_path / "test_mycam.db")
    storage_dir = str(tmp_path / "captures")
    os.environ["MYCAM_DB_PATH"] = db_file
    os.environ["SOVEREIGN_ENCRYPTION_KEY"] = "g18X4J5ZpX5q8Q7L6T1Y2U3V4W5X6Y7Z8A9B0C1D2E3="
    config = {
        "storage_dir": storage_dir,
        "encryption_enabled": True,
        "encryption_key": os.environ["SOVEREIGN_ENCRYPTION_KEY"],
        "retention_days": 30,
        "alexa_bridge_enabled": False
    }
    yield {
        "config": config,
        "db_file": db_file,
        "storage_dir": storage_dir,
        "tmp_path": tmp_path
    }
    if "MYCAM_DB_PATH" in os.environ:
        del os.environ["MYCAM_DB_PATH"]


def test_vault_crypto(temp_env):
    config = temp_env["config"]
    plaintext = "Sensitive Sentinel Telemetry Payload"

    # 1. Encryption
    encrypted = encrypt_payload(plaintext, config)
    assert encrypted.startswith("enc:")
    assert encrypted != plaintext

    # 2. Decryption
    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == plaintext

    # 3. SHA-256 computation
    content_hash = compute_sha256(plaintext)
    assert len(content_hash) == 64
    assert isinstance(content_hash, str)


def test_storage_and_ledger(temp_env):
    config = temp_env["config"]
    init_sqlite_ledger(config)

    # Log Event
    event = log_event(config, "test_trigger", "Front Doorbell Motion", [], "Test event details")
    assert event["id"].startswith("evt_")
    assert event["notification_title"] == "Front Doorbell Motion"

    # Verify SQLite schema tables created
    conn = sqlite3.connect(temp_env["db_file"])
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()

    assert "hot_pool" in tables
    assert "warm_pool" in tables
    assert "cold_storage" in tables
    assert "telemetry_events" in tables
    assert "known_identities" in tables


def test_known_identities(temp_env):
    config = temp_env["config"]
    insert_known_identity(
        identity_id="id_test_001",
        name="User Profile",
        source="test_source",
        file_hash="abc123hash",
        local_path="/tmp/fake.jpg",
        metadata_dict={"type": "owner"},
        vector_list=[0.1] * 768,
        config=config
    )

    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["id"] == "id_test_001"
    assert identities[0]["name"] == "User Profile"
    assert identities[0]["has_vector"] is True


def test_training_label_promotion(temp_env):
    config = temp_env["config"]
    event_id = "evt_123456"

    log_event(config, "test_trigger", "Motion Flag", [], details="Testing promotion")
    update_training_label(event_id, "APPROVED_KNOWN", config)

    # Check Cold Storage has sealed record
    conn = sqlite3.connect(temp_env["db_file"])
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM cold_storage;")
    count = cursor.fetchone()[0]
    conn.close()

    assert count >= 1


def test_cleon_dynasty_gate(temp_env):
    config = temp_env["config"]

    # 1. Gate 1 Dawn Rejection (Noise trigger)
    res_noise = evaluate_cleon_trip("Unrelated System Update", config=config)
    assert res_noise["action_taken"] == "SUPPRESSED_BY_DAWN"
    assert res_noise["gate_1_dawn"]["passed"] is False

    # 2. Gate 2 Day & Gate 3 Dusk (Friendly Trip)
    insert_known_identity(
        identity_id="id_mom_001",
        name="Mom",
        source="family",
        file_hash="hash_mom_123",
        local_path="/tmp/mom.jpg",
        metadata_dict={},
        config=config
    )
    res_friendly = evaluate_cleon_trip("Mom walking to Front Door Camera", config=config)
    assert res_friendly["gate_1_dawn"]["passed"] is True
    assert res_friendly["gate_2_day"]["classification"] == "FRIENDLY_VERIFIED"
    assert res_friendly["action_taken"] == "SEALED_SILENT_GOLD"

    # 3. Gate 2 Day & Gate 3 Dusk (Unrecognized Stranger Trip)
    res_stranger = evaluate_cleon_trip("Motion detected on Backporch Floodlight", config=config)
    assert res_stranger["gate_1_dawn"]["passed"] is True
    assert res_stranger["gate_2_day"]["classification"] == "UNRECOGNIZED_ANOMALY"
    assert res_stranger["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"


def test_alexa_bridge():
    ip = get_local_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4

    trigger_alexa_alert("Unit Test Pulse")
    # State briefly pulses to "1"
    # Wait for background reset thread
    time.sleep(2.5)


def test_photos_ingest(temp_env):
    config = temp_env["config"]
    tmp_dir = temp_env["tmp_path"] / "photos"
    tmp_dir.mkdir()

    # Create test image
    img_path = str(tmp_dir / "test_photo.jpg")
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(img_path)

    identities_dir = str(temp_env["tmp_path"] / "identities")
    os.makedirs(identities_dir, exist_ok=True)

    sha = compute_file_sha256(img_path)
    assert len(sha) == 64

    ingested = ingest_from_directory(str(tmp_dir), identities_dir, limit=10, config=config)
    assert ingested == 1


def test_video_compile(temp_env):
    event_folder = str(temp_env["tmp_path"] / "event_frames")
    os.makedirs(event_folder, exist_ok=True)

    # Create 3 synthetic PNG frames
    for i in range(3):
        fpath = os.path.join(event_folder, f"frame_{i:04d}.png")
        img = Image.new("RGB", (64, 64), color="red" if i % 2 == 0 else "green")
        img.save(fpath)

    result_path = compile_frames_to_animation(event_folder, output_format="gif", fps=5)
    assert result_path is not None
    assert os.path.exists(result_path)
