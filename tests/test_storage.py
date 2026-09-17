import os
import sqlite3
import json
import pytest
from datetime import datetime, timedelta
from storage import (
    get_storage_dir,
    get_db_paths,
    init_sqlite_ledger,
    write_to_sqlite,
    log_event,
    load_events,
    save_events,
    update_training_label,
    insert_known_identity,
    get_known_identities,
    cleanup_old_media
)

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_mycam.db")
    storage_dir = str(tmp_path / "captures")
    events_file = str(tmp_path / "events.json")

    monkeypatch.setenv("MYCAM_DB_PATH", db_path)
    monkeypatch.setattr("storage.EVENTS_FILE", events_file)

    config = {
        "storage_dir": storage_dir,
        "retention_days": 7
    }
    return config, db_path, storage_dir, events_file

def test_init_sqlite_ledger(temp_env):
    config, db_path, _, _ = temp_env
    init_sqlite_ledger(config)

    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ["hot_pool", "warm_pool", "cold_storage", "telemetry_events", "known_identities"]
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
        assert cursor.fetchone() is not None, f"Table {table} missing"
    conn.close()

def test_write_and_update_sqlite(temp_env):
    config, db_path, _, _ = temp_env
    write_to_sqlite("evt_101", "test_source", "motion_alert", {"info": "test_data"}, config=config)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, event_type FROM telemetry_events WHERE id='evt_101';")
    row = cursor.fetchone()
    assert row == ("evt_101", "test_source", "motion_alert")
    conn.close()

    update_training_label("evt_101", "PERSON_VERIFIED", config=config)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT training_label FROM telemetry_events WHERE id='evt_101';")
    row = cursor.fetchone()
    assert row[0] == "PERSON_VERIFIED"

    cursor.execute("SELECT COUNT(*) FROM warm_pool;")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT COUNT(*) FROM cold_storage;")
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_log_and_load_events(temp_env):
    config, _, storage_dir, _ = temp_env
    evt = log_event(config, "test_trigger", "Test Notification Title", ["path1.png"], details="Test details")

    assert evt["id"].startswith("evt_")
    assert evt["trigger_type"] == "test_trigger"

    events = load_events(config)
    assert len(events) >= 1
    assert events[0]["id"] == evt["id"]

def test_identities_storage(temp_env):
    config, db_path, _, _ = temp_env
    insert_known_identity(
        identity_id="id_001",
        name="John Doe",
        source="unit_test",
        file_hash="hash123456789",
        local_path="/tmp/john.png",
        metadata_dict={"tag": "family"},
        vector_list=[0.1] * 768,
        config=config
    )

    identities = get_known_identities(config)
    assert len(identities) == 1
    assert identities[0]["name"] == "John Doe"
    assert identities[0]["has_vector"] is True

def test_cleanup_old_media(temp_env, tmp_path):
    config, _, storage_dir, events_file = temp_env

    old_file = str(tmp_path / "old.png")
    new_file = str(tmp_path / "new.png")
    with open(old_file, "w") as f: f.write("old")
    with open(new_file, "w") as f: f.write("new")

    old_time = (datetime.now() - timedelta(days=10)).isoformat()
    new_time = datetime.now().isoformat()

    events = [
        {"id": "evt_old", "timestamp": old_time, "media": [old_file]},
        {"id": "evt_new", "timestamp": new_time, "media": [new_file]}
    ]
    save_events(events)

    cleanup_old_media(config)

    assert not os.path.exists(old_file)
    assert os.path.exists(new_file)
