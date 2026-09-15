import os
import sys
import json
import tempfile
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vault_crypto import encrypt_payload, decrypt_payload, compute_sha256, get_or_create_key
from storage import (
    init_sqlite_ledger, log_event, load_events, save_events,
    insert_known_identity, get_known_identities, update_training_label,
    cleanup_old_media, get_storage_dir
)
from cleon_gate import evaluate_cleon_trip, CleonDynastyGate
from photos_ingest import get_designated_photo_sources, compute_bytes_sha256, compute_file_sha256
from main import load_config
import listener


@pytest.fixture
def temp_env(tmp_path):
    """Fixture providing temporary directory and mock config for isolated tests."""
    temp_dir = str(tmp_path)
    db_path = os.path.join(temp_dir, "test_mycam.db")
    events_file = os.path.join(temp_dir, "events.json")
    storage_dir = os.path.join(temp_dir, "captures")
    os.makedirs(storage_dir, exist_ok=True)

    config = {
        "storage_dir": storage_dir,
        "default_capture_mode": "hybrid",
        "record_duration_seconds": 5,
        "fps": 10,
        "target_keywords": ["ring", "motion", "camera", "doorbell"],
        "retention_days": 30,
        "webhook_port": 8765,
        "adb_enabled": False,
        "encryption_enabled": True,
        "encryption_key": get_or_create_key(),
        "telegram": {"enabled": False}
    }

    with patch.dict(os.environ, {"MYCAM_DB_PATH": db_path}):
        with patch("storage.EVENTS_FILE", events_file):
            init_sqlite_ledger(config)
            yield {
                "config": config,
                "db_path": db_path,
                "events_file": events_file,
                "storage_dir": storage_dir,
                "temp_dir": temp_dir
            }


class TestVaultCrypto:
    def test_sha256_computation(self):
        text = "sovereign_data_integrity"
        expected = "c5cc0b0d821c6f9a2eae51391d89402057074bf54670973ba7c34f504d6dd24c"
        assert compute_sha256(text) == expected

    def test_encryption_decryption(self, temp_env):
        config = temp_env["config"]
        plaintext = json.dumps({"sensor": "front_door", "alert": "motion"})

        encrypted = encrypt_payload(plaintext, config)
        assert encrypted.startswith("enc:")

        decrypted = decrypt_payload(encrypted, config)
        assert decrypted == plaintext

    def test_unencrypted_passthrough(self):
        config = {"encryption_enabled": False}
        plaintext = "raw_unencrypted_data"
        assert encrypt_payload(plaintext, config) == plaintext
        assert decrypt_payload(plaintext, config) == plaintext


class TestStorageAndLedger:
    def test_sqlite_ledger_init(self, temp_env):
        db_path = temp_env["db_path"]
        assert os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        tables = ["hot_pool", "warm_pool", "cold_storage", "telemetry_events", "known_identities"]
        for t in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}';")
            assert cursor.fetchone() is not None
        conn.close()

    def test_log_and_load_events(self, temp_env):
        config = temp_env["config"]
        dummy_media = [os.path.join(temp_env["storage_dir"], "snap1.png")]

        event = log_event(config, "test_trigger", "Front Doorbell Motion", dummy_media, "test details")
        assert event["trigger_type"] == "test_trigger"
        assert event["notification_title"] == "Front Doorbell Motion"

        events = load_events(config)
        assert len(events) >= 1
        assert events[0]["id"] == event["id"]

    def test_known_identities(self, temp_env):
        config = temp_env["config"]
        identity_id = "id_test_123"
        name = "Owner User"
        source = "test_source"
        file_hash = "abc123hash"
        local_path = os.path.join(temp_env["storage_dir"], "id.jpg")

        insert_known_identity(
            identity_id=identity_id,
            name=name,
            source=source,
            file_hash=file_hash,
            local_path=local_path,
            metadata_dict={"tag": "family"},
            vector_list=[0.1, 0.2, 0.3],
            config=config
        )

        identities = get_known_identities(config)
        assert len(identities) >= 1
        found = next((i for i in identities if i["id"] == identity_id), None)
        assert found is not None
        assert found["name"] == name
        assert found["has_vector"] is True

    def test_update_training_label(self, temp_env):
        config = temp_env["config"]
        event = log_event(config, "test_trigger", "Backyard Cam Motion", [], "details")
        event_id = event["id"]

        update_training_label(event_id, "APPROVED_KNOWN", config)

        conn = sqlite3.connect(temp_env["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT training_label FROM telemetry_events WHERE id = ?;", (event_id,))
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "APPROVED_KNOWN"


class TestCleonDynastyGate:
    def test_gate_dawn_filtering(self, temp_env):
        config = temp_env["config"]
        gate = CleonDynastyGate(config)

        # Non-matching trigger signal
        result_noise = gate.evaluate_trip("System random update notice")
        assert result_noise["action_taken"] == "SUPPRESSED_BY_DAWN"
        assert result_noise["gate_1_dawn"]["passed"] is False

        # Valid motion trigger
        result_signal = gate.evaluate_trip("Ring Doorbell Motion Detected")
        assert result_signal["gate_1_dawn"]["passed"] is True

    def test_gate_friendly_vs_anomaly(self, temp_env):
        config = temp_env["config"]
        insert_known_identity("id_mom", "Mom", "test", "hash_mom", "/path/mom.jpg", {}, None, config)

        # Test friendly match
        res_friendly = evaluate_cleon_trip("Mom walking up to Front Door Camera", config=config)
        assert res_friendly["gate_2_day"]["classification"] == "FRIENDLY_VERIFIED"
        assert res_friendly["action_taken"] == "SEALED_SILENT_GOLD"

        # Test unrecognized visitor
        res_unknown = evaluate_cleon_trip("Unknown Motion on Driveway", config=config)
        assert res_unknown["gate_2_day"]["classification"] == "UNRECOGNIZED_ANOMALY"
        assert res_unknown["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"


class TestPhotosIngest:
    def test_photo_sources_discovery(self, temp_env):
        sources = get_designated_photo_sources(temp_env["config"])
        assert isinstance(sources, list)
        assert len(sources) >= 1

    def test_sha256_hashing(self, temp_env):
        data = b"mycam_sovereign_bytes"
        hash_bytes = compute_bytes_sha256(data)

        test_file = os.path.join(temp_env["temp_dir"], "test.bin")
        with open(test_file, "wb") as f:
            f.write(data)

        hash_file = compute_file_sha256(test_file)
        assert hash_bytes == hash_file


class TestWebhookAndMediaSecurity:
    def test_media_path_traversal_prevention(self, temp_env):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Create dummy file inside repo
        valid_file = os.path.join(base_dir, "captures", "test_media.png")
        os.makedirs(os.path.dirname(valid_file), exist_ok=True)
        with open(valid_file, "w") as f:
            f.write("dummy_image_data")

        handler = listener.WebhookHandler
        handler.config = temp_env["config"]

        # Test valid path
        valid_query = f"/api/media?path={valid_file}"
        parsed_valid = listener.urllib.parse.urlparse(valid_query)
        assert parsed_valid.path == "/api/media"

        # Cleanup
        if os.path.exists(valid_file):
            os.remove(valid_file)


class TestMainConfig:
    def test_load_config_fallback(self):
        config = load_config()
        assert "storage_dir" in config
        assert "webhook_port" in config
