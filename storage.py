import os
import json
import sqlite3
from datetime import datetime, timedelta

EVENTS_FILE = "events.json"

def get_storage_dir(config=None):
    if config is None:
        config = {}
    storage_dir = config.get("storage_dir", "captures")
    if not os.path.isabs(storage_dir):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        storage_dir = os.path.join(base_dir, storage_dir)
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir

def get_db_paths(config=None):
    paths = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    primary_db = os.environ.get("MYCAM_DB_PATH", os.path.join(base_dir, "mycam.db"))
    paths.append(primary_db)

    # Optional external mesh or spoke database path
    external_db = os.environ.get("MYCAM_EXTERNAL_LEDGER_PATH")
    if external_db and os.path.exists(os.path.dirname(external_db)):
        paths.append(external_db)
        
    return paths

def init_sqlite_ledger(config=None):
    for db_path in get_db_paths(config):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                event_type TEXT,
                payload_json TEXT,
                frame_path TEXT,
                training_label TEXT,
                reviewed_at DATETIME,
                git_commit_sha TEXT
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_events(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_source ON telemetry_events(source);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_event_type ON telemetry_events(event_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_label ON telemetry_events(training_label);")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Init failed for {db_path}: {e}")

def write_to_sqlite(event_id, source, event_type, payload, frame_path=None, git_sha=None, config=None):
    init_sqlite_ledger(config)
    for db_path in get_db_paths(config):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO telemetry_events (id, timestamp, source, event_type, payload_json, frame_path, git_commit_sha)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (event_id, datetime.now().isoformat(), source, event_type, json.dumps(payload), frame_path, git_sha))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Insert failed for {db_path}: {e}")

def update_training_label(event_id, label, config=None):
    init_sqlite_ledger(config)
    for db_path in get_db_paths(config):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE telemetry_events 
            SET training_label = ?, reviewed_at = ?
            WHERE id = ?;
            """, (label, datetime.now().isoformat(), event_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Update label failed for {db_path}: {e}")

def load_events():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    evt_path = os.path.join(base_dir, EVENTS_FILE)
    if os.path.exists(evt_path):
        try:
            with open(evt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_events(events):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    evt_path = os.path.join(base_dir, EVENTS_FILE)
    with open(evt_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

def log_event(config, trigger_type, notification_title, media_files, details=""):
    events = load_events()
    event_id = f"evt_{int(datetime.now().timestamp())}"
    primary_media = media_files[0] if media_files else None
    
    event_entry = {
        "id": event_id,
        "timestamp": datetime.now().isoformat(),
        "trigger_type": trigger_type,
        "notification_title": notification_title,
        "media": media_files,
        "details": details
    }
    events.insert(0, event_entry)
    save_events(events)
    
    # Node detection from environment
    node_name = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "local-sentinel"))
    
    payload = {
        "title": notification_title,
        "details": details,
        "media_files": media_files,
        "node": node_name,
        "mode": trigger_type
    }
    write_to_sqlite(
        event_id=event_id,
        source="myCam_Sentinel",
        event_type=trigger_type,
        payload=payload,
        frame_path=primary_media,
        config=config
    )
    return event_entry

def cleanup_old_media(config):
    retention_days = config.get("retention_days", 30)
    cutoff = datetime.now() - timedelta(days=retention_days)
    events = load_events()
    updated_events = []
    
    for evt in events:
        try:
            evt_time = datetime.fromisoformat(evt["timestamp"])
            if evt_time < cutoff:
                for media_path in evt.get("media", []):
                    if os.path.exists(media_path):
                        os.remove(media_path)
            else:
                updated_events.append(evt)
        except Exception:
            updated_events.append(evt)
            
    save_events(updated_events)
