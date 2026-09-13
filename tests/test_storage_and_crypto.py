import os
import json
import tempfile
import pytest
from datetime import datetime, timedelta

from vault_crypto import get_or_create_key, encrypt_payload, decrypt_payload, compute_sha256
from storage import (
    get_storage_dir,
    get_db_paths,
    init_sqlite_ledger,
    write_to_sqlite,
    update_training_label,
    load_events,
    save_events,
    log_event,
    cleanup_old_media,
    insert_known_identity,
    get_known_identities,
)

def test_vault_crypto_hash_and_key():
    val = "hello world"
    expected_hash = compute_sha256(val)
    assert len(expected_hash) == 64
    assert compute_sha256(val) == expected_hash

    config = {}
    key = get_or_create_key(config)
    assert key is not None and len(key) > 0

def test_vault_crypto_encryption_disabled():
    config = {"encryption_enabled": False}
    payload = "plaintext data"
    enc = encrypt_payload(payload, config)
    assert enc == payload
    dec = decrypt_payload(enc, config)
    assert dec == payload

def test_vault_crypto_encryption_enabled():
    config = {"encryption_enabled": True}
    payload = json.dumps({"test": "data", "number": 123})
    enc = encrypt_payload(payload, config)
    assert enc.startswith("enc:")
    assert enc != payload
    dec = decrypt_payload(enc, config)
    assert dec == payload

def test_storage_lifecycle(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_mycam.db")
    test_storage = str(tmp_path / "captures")
    monkeypatch.setenv("MYCAM_DB_PATH", test_db)
    monkeypatch.chdir(tmp_path)

    config = {
        "storage_dir": test_storage,
        "encryption_enabled": True,
        "retention_days": 1
    }

    # Init SQLite ledger
    init_sqlite_ledger(config)
    assert os.path.exists(test_db)

    # Log event
    dummy_media = str(tmp_path / "test.png")
    with open(dummy_media, "w") as f:
        f.write("dummy")

    evt = log_event(config, "test_trigger", "Test Alert Title", [dummy_media], "Test Details")
    assert evt["id"].startswith("evt_")
    assert evt["notification_title"] == "Test Alert Title"

    events = load_events(config)
    assert len(events) >= 1
    assert events[0]["notification_title"] == "Test Alert Title"

    # Update training label
    update_training_label(evt["id"], "person", config)

    # Identity Enrollment
    insert_known_identity(
        identity_id="id_test123",
        name="John Doe",
        source="test_source",
        file_hash="hash1234567890",
        local_path=dummy_media,
        metadata_dict={"test": "meta"},
        vector_list=[0.1] * 768,
        config=config
    )

    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["name"] == "John Doe"
    assert identities[0]["has_vector"] is True

    # Retention Cleanup Test
    old_event = {
        "id": "evt_old",
        "timestamp": (datetime.now() - timedelta(days=5)).isoformat(),
        "trigger_type": "old_type",
        "notification_title": "Old Alert",
        "media": [dummy_media],
        "details": "Old Details"
    }
    events.append(old_event)
    save_events(events)

    cleanup_old_media(config)
    # The dummy media file should be removed by cleanup because old_event was older than retention_days (1)
    assert not os.path.exists(dummy_media)
