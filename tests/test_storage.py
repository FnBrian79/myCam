import os
import tempfile
import sqlite3
import pytest
from storage import (
    init_sqlite_ledger,
    write_to_sqlite,
    update_training_label,
    insert_known_identity,
    get_known_identities,
    log_event,
    load_events,
    save_events,
    cleanup_old_media
)

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_mycam.db")
    monkeypatch.setenv("MYCAM_DB_PATH", db_file)
    events_json = str(tmp_path / "events.json")

    config = {
        "storage_dir": str(tmp_path / "captures"),
        "retention_days": 1
    }
    return db_file, config

def test_init_sqlite_ledger(temp_env):
    db_file, config = temp_env
    init_sqlite_ledger(config)
    assert os.path.exists(db_file)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "hot_pool" in tables
    assert "warm_pool" in tables
    assert "cold_storage" in tables
    assert "telemetry_events" in tables
    assert "known_identities" in tables

def test_write_and_update_pools(temp_env):
    db_file, config = temp_env
    event_id = "evt_test_123"
    payload = {"motion": True, "cam": "Front Door"}

    write_to_sqlite(event_id, "test_source", "motion_alert", payload, config=config)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT source FROM hot_pool;")
    hot_row = cursor.fetchone()
    assert hot_row[0] == "test_source"
    conn.close()

    update_training_label(event_id, "APPROVED_KNOWN", config=config)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT context_summary FROM warm_pool;")
    warm_row = cursor.fetchone()
    assert "APPROVED_KNOWN" in warm_row[0]

    cursor.execute("SELECT hash FROM cold_storage;")
    cold_row = cursor.fetchone()
    assert cold_row is not None
    conn.close()

def test_known_identities(temp_env):
    db_file, config = temp_env
    insert_known_identity(
        identity_id="id_mom_001",
        name="Mom",
        source="unit_test",
        file_hash="hash_mom_123456789",
        local_path="/fake/mom.jpg",
        metadata_dict={"relation": "mother"},
        vector_list=[0.1, 0.2, 0.3],
        config=config
    )

    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["name"] == "Mom"
    assert identities[0]["has_vector"] is True
    assert identities[0]["metadata"]["relation"] == "mother"

def test_log_and_load_events(tmp_path, monkeypatch):
    base_dir = tmp_path
    events_path = str(base_dir / "events.json")

    config = {
        "storage_dir": str(tmp_path / "captures")
    }

    # Patch EVENTS_FILE in storage module context
    import storage
    monkeypatch.setattr(storage, "EVENTS_FILE", events_path)

    entry = log_event(config, "test_trigger", "Test Motion Alert", [], details="Test Details")
    assert entry["notification_title"] == "Test Motion Alert"

    loaded = load_events(config)
    assert len(loaded) >= 1
    assert loaded[0]["notification_title"] == "Test Motion Alert"
