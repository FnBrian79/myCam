import os
import sqlite3
import json
from datetime import datetime, timedelta
import pytest
from storage import (
    get_storage_dir,
    get_db_paths,
    init_sqlite_ledger,
    write_to_sqlite,
    update_training_label,
    log_event,
    load_events,
    cleanup_old_media
)

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    storage_d = str(tmp_path / "captures")
    db_p = str(tmp_path / "test_mycam.db")
    events_p = str(tmp_path / "events.json")

    monkeypatch.setenv("MYCAM_DB_PATH", db_p)
    config = {"storage_dir": storage_d, "retention_days": 30}
    return config, db_p, events_p

def test_get_storage_dir(temp_env):
    config, _, _ = temp_env
    s_dir = get_storage_dir(config)
    assert os.path.exists(s_dir)

def test_sqlite_ledger_and_write(temp_env):
    config, db_p, _ = temp_env
    init_sqlite_ledger(config)

    write_to_sqlite(
        event_id="evt_test_1",
        source="test_source",
        event_type="test_trigger",
        payload={"msg": "hello"},
        frame_path="/tmp/frame.png",
        config=config
    )

    conn = sqlite3.connect(db_p)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, status FROM hot_pool")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "test_source"

    cursor.execute("SELECT id, source, event_type FROM telemetry_events")
    te_rows = cursor.fetchall()
    assert len(te_rows) == 1
    assert te_rows[0][0] == "evt_test_1"
    conn.close()

def test_update_training_label(temp_env):
    config, db_p, _ = temp_env
    init_sqlite_ledger(config)

    write_to_sqlite("evt_label_1", "test", "motion", {"foo": "bar"}, config=config)
    update_training_label("evt_label_1", "APPROVED_KNOWN", config)

    conn = sqlite3.connect(db_p)
    cursor = conn.cursor()
    cursor.execute("SELECT training_label FROM telemetry_events WHERE id = 'evt_label_1'")
    row = cursor.fetchone()
    assert row[0] == "APPROVED_KNOWN"

    cursor.execute("SELECT COUNT(*) FROM warm_pool")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT COUNT(*) FROM cold_storage")
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_log_event_and_load_events(temp_env, monkeypatch):
    config, _, _ = temp_env
    # Patch EVENTS_FILE location by overriding base path or working directory
    base_dir = str(os.path.dirname(os.path.abspath(__file__)))

    evt_entry = log_event(config, "test_mode", "Test Notification Title", ["/tmp/test.png"], "Details here")
    assert evt_entry["id"].startswith("evt_")
    assert evt_entry["notification_title"] == "Test Notification Title"

def test_cleanup_old_media(temp_env, monkeypatch):
    config, _, _ = temp_env
    media_dir = get_storage_dir(config)
    old_file = os.path.join(media_dir, "old_media.png")
    with open(old_file, "w") as f:
        f.write("dummy")

    old_timestamp = (datetime.now() - timedelta(days=40)).isoformat()
    old_event = {
        "id": "evt_old",
        "timestamp": old_timestamp,
        "trigger_type": "old",
        "notification_title": "Old Event",
        "media": [old_file],
        "details": ""
    }

    # Patch save_events and load_events
    monkeypatch.setattr("storage.load_events", lambda config=None: [old_event])
    saved = []
    monkeypatch.setattr("storage.save_events", lambda events: saved.extend(events))

    cleanup_old_media(config)
    assert not os.path.exists(old_file)
    assert len(saved) == 0
