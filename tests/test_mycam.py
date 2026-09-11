import os
import sys
import json
import tempfile
import sqlite3
import pytest
from cryptography.fernet import Fernet
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault_crypto import encrypt_payload, decrypt_payload, compute_sha256, get_or_create_key
from storage import (
    init_sqlite_ledger,
    write_to_sqlite,
    load_events,
    save_events,
    log_event,
    cleanup_old_media,
    insert_known_identity,
    get_known_identities,
    update_training_label
)
from cleon_gate import CleonDynastyGate, evaluate_cleon_trip, cosine_similarity
from recorder import capture_screenshot, capture_sequence
from video import compile_frames_to_animation
from photos_ingest import compute_bytes_sha256, compute_file_sha256
from telegram_feed import handle_telegram_callback, send_telegram_alert

@pytest.fixture
def temp_env(tmp_path):
    """Creates a temporary isolated environment for testing."""
    storage_dir = str(tmp_path / "captures")
    db_path = str(tmp_path / "test_mycam.db")
    valid_fernet_key = Fernet.generate_key().decode("utf-8")

    config = {
        "storage_dir": storage_dir,
        "default_capture_mode": "hybrid",
        "record_duration_seconds": 15,
        "fps": 10,
        "target_keywords": ["ring", "motion", "camera"],
        "retention_days": 30,
        "webhook_port": 8765,
        "adb_enabled": False,
        "encryption_enabled": True,
        "encryption_key": valid_fernet_key
    }

    with patch.dict(os.environ, {"MYCAM_DB_PATH": db_path}):
        init_sqlite_ledger(config)
        yield config, db_path, storage_dir

# ============================================================================
# 1. VAULT CRYPTO TESTS
# ============================================================================
def test_vault_crypto_sha256():
    data = "Sovereign myCam Vault Test"
    hash1 = compute_sha256(data)
    hash2 = compute_sha256(data)
    assert len(hash1) == 64
    assert hash1 == hash2

def test_vault_crypto_encryption(temp_env):
    config, _, _ = temp_env
    plaintext = '{"event": "motion_detected", "location": "front_door"}'

    encrypted = encrypt_payload(plaintext, config)
    assert encrypted.startswith("enc:")

    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == plaintext

def test_vault_crypto_disabled():
    config = {"encryption_enabled": False}
    plaintext = "Unencrypted Data"
    res = encrypt_payload(plaintext, config)
    assert res == plaintext
    assert decrypt_payload(res, config) == plaintext

# ============================================================================
# 2. STORAGE & LEDGER TESTS
# ============================================================================
def test_storage_init_and_write(temp_env):
    config, db_path, _ = temp_env

    event = log_event(config, "test_trigger", "Front Porch Motion", [], details="Test Details")
    assert event["notification_title"] == "Front Porch Motion"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM hot_pool;")
    count = cursor.fetchone()[0]
    assert count >= 1
    conn.close()

def test_known_identities(temp_env):
    config, db_path, storage_dir = temp_env

    dummy_vec = [0.1] * 768
    insert_known_identity(
        identity_id="id_12345",
        name="Alice",
        source="test_folder",
        file_hash="hash_1234567890",
        local_path="/tmp/alice.jpg",
        metadata_dict={"tag": "family"},
        vector_list=dummy_vec,
        config=config
    )

    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["name"] == "Alice"
    assert identities[0]["has_vector"] is True
    assert len(identities[0]["vector_768"]) == 768

def test_training_label_update(temp_env):
    config, db_path, _ = temp_env
    event_id = "evt_99999"

    update_training_label(event_id, "APPROVED_KNOWN", config)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT context_summary FROM warm_pool WHERE metadata LIKE ?;", (f"%{event_id}%",))
    row = cursor.fetchone()
    assert row is not None
    assert "APPROVED_KNOWN" in row[0]
    conn.close()

# ============================================================================
# 3. CLEON DYNASTY GATE TESTS
# ============================================================================
def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3)) == 0.0

def test_cleon_gate_dawn_filtering(temp_env):
    config, _, _ = temp_env
    gate = CleonDynastyGate(config)

    # Noise trigger should fail Dawn
    res_noise = gate.evaluate_trip("Random system heartbeat noise")
    assert res_noise["action_taken"] == "SUPPRESSED_BY_DAWN"
    assert res_noise["gate_1_dawn"]["passed"] is False

    # Motion trigger should pass Dawn
    res_valid = gate.evaluate_trip("Front Doorbell Motion Alert")
    assert res_valid["gate_1_dawn"]["passed"] is True

def test_cleon_gate_day_and_dusk(temp_env):
    config, _, _ = temp_env

    # Enroll a known identity 'Mom'
    insert_known_identity(
        identity_id="id_mom",
        name="Mom",
        source="takeout",
        file_hash="hash_mom_123",
        local_path="/tmp/mom.jpg",
        metadata_dict={},
        vector_list=[0.5] * 768,
        config=config
    )

    gate = CleonDynastyGate(config)

    # Friendly trip mentioning Mom
    res_friendly = gate.evaluate_trip("Mom arriving at Front Door Camera")
    assert res_friendly["gate_2_day"]["classification"] == "FRIENDLY_VERIFIED"
    assert res_friendly["action_taken"] == "SEALED_SILENT_GOLD"

    # Unrecognized trip
    res_stranger = gate.evaluate_trip("Motion detected on Backporch Camera")
    assert res_stranger["gate_2_day"]["classification"] == "UNRECOGNIZED_ANOMALY"
    assert res_stranger["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"

# ============================================================================
# 4. RECORDER & VIDEO TESTS
# ============================================================================
def test_recorder_snapshot(temp_env):
    config, _, storage_dir = temp_env

    with patch("recorder.grab_screen") as mock_grab:
        from PIL import Image
        mock_img = Image.new("RGB", (100, 100), color="red")
        mock_grab.return_value = mock_img

        filepath = capture_screenshot(config, title="Unit Test Snapshot")
        assert filepath is not None
        assert os.path.exists(filepath)

def test_recorder_sequence_and_compile(temp_env):
    config, _, storage_dir = temp_env

    with patch("recorder.grab_screen") as mock_grab:
        from PIL import Image
        mock_grab.return_value = Image.new("RGB", (50, 50), color="blue")

        files = capture_sequence(config, duration_sec=1, fps=2, title="Test Sequence")
        assert len(files) >= 2

        event_folder = os.path.dirname(files[0])
        anim_path = compile_frames_to_animation(event_folder, output_format="gif", fps=2)
        assert anim_path is not None
        assert os.path.exists(anim_path)

# ============================================================================
# 5. TELEGRAM FEED & CALLBACK TESTS
# ============================================================================
def test_telegram_callback_handler(temp_env):
    config, _, _ = temp_env

    success, msg = handle_telegram_callback("act:evt_1001:approve", config)
    assert success is True
    assert "Approved" in msg

    success_lbl, msg_lbl = handle_telegram_callback("lbl:evt_1001:person", config)
    assert success_lbl is True
    assert "person" in msg_lbl

def test_telegram_send_alert_list_path(temp_env):
    config, _, _ = temp_env
    config["telegram"] = {"enabled": False}

    # Passing list of media paths shouldn't crash
    res = send_telegram_alert(config, "evt_test", "Alert Title", media_path=["/tmp/a.jpg", "/tmp/b.jpg"])
    assert res is False
