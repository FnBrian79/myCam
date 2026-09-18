import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from vault_crypto import encrypt_payload, decrypt_payload, compute_sha256

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
    """Resolves SQLite storage paths, including the 3-Tier Hot/Warm/Cold pools."""
    paths = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    primary_db = os.environ.get("MYCAM_DB_PATH", os.path.join(base_dir, "mycam.db"))
    paths.append(primary_db)

    # Optional 3-Tier Mesh Hot Pool paths
    hot_pool_env = os.environ.get("HOT_POOL_PATH")
    if hot_pool_env:
        paths.append(hot_pool_env)

    external_db = os.environ.get("MYCAM_EXTERNAL_LEDGER_PATH")
    if external_db and os.path.exists(os.path.dirname(external_db)):
        paths.append(external_db)
        
    return list(dict.fromkeys(paths))

def init_sqlite_ledger(config=None):
    """Initializes high-speed WAL mode and the Tri-Stage schema (Hot Pool, Warm Pool, Cold Storage)."""
    for db_path in get_db_paths(config):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            # High-speed concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")

            # 1. HOT POOL: Ephemeral, high-frequency raw telemetry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hot_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT,
                payload TEXT, -- JSON blob (encrypted if encryption_enabled)
                status TEXT DEFAULT 'PENDING' -- PENDING, GOLD, GRUB
            );
            """)

            # 2. WARM POOL: Triaged & training context
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS warm_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                timestamp TEXT,
                context_summary TEXT,
                metadata TEXT
            );
            """)

            # 3. COLD STORAGE: Immutable sealed lineage snapshots
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cold_storage (
                hash TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                sealed_at TEXT NOT NULL,
                full_state TEXT NOT NULL
            );
            """)

            # 4. Standard telemetry events table for backward-compatible dashboard queries
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hot_status ON hot_pool(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_label ON telemetry_events(training_label);")

            # 5. Known identities & visual reference library
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_identities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT,
                file_hash TEXT UNIQUE,
                local_path TEXT,
                metadata_json TEXT,
                vector_768 TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_identity_hash ON known_identities(file_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_identity_name ON known_identities(name);")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Init failed for {db_path}: {e}")

def write_to_sqlite(event_id, source, event_type, payload, frame_path=None, git_sha=None, config=None):
    init_sqlite_ledger(config)
    node_name = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "local-sentinel"))
    raw_payload_str = json.dumps(payload)
    vault_payload_str = encrypt_payload(raw_payload_str, config)

    for db_path in get_db_paths(config):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            # Write to Tier 1: Hot Pool
            cursor.execute("""
            INSERT INTO hot_pool (timestamp, source, payload, status)
            VALUES (?, ?, ?, 'PENDING');
            """, (datetime.now(timezone.utc).isoformat(), source, vault_payload_str))

            # Write to Telemetry Events (for Dashboard & Ledger)
            cursor.execute("""
            INSERT OR REPLACE INTO telemetry_events (id, timestamp, source, event_type, payload_json, frame_path, git_commit_sha)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (event_id, datetime.now().isoformat(), source, event_type, vault_payload_str, frame_path, git_sha))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Hot pool insert failed for {db_path}: {e}")

def update_training_label(event_id, label, config=None):
    """Promotes event from Hot Pool into Warm Pool triage and Cold sealed storage."""
    init_sqlite_ledger(config)
    node_name = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "local-sentinel"))
    
    for db_path in get_db_paths(config):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            # 1. Update Telemetry Event
            cursor.execute("""
            UPDATE telemetry_events 
            SET training_label = ?, reviewed_at = ?
            WHERE id = ?;
            """, (label, datetime.now().isoformat(), event_id))

            # 2. Promote to Tier 2: Warm Pool
            summary = f"Motion Event {event_id} verified as: {label}"
            cursor.execute("""
            INSERT INTO warm_pool (node_id, timestamp, context_summary, metadata)
            VALUES (?, ?, ?, ?);
            """, (node_name, datetime.now(timezone.utc).isoformat(), summary, json.dumps({"label": label, "event_id": event_id})))

            # 3. Seal into Tier 3: Cold Storage (Immutable Snapshot with SHA-256)
            full_state = json.dumps({
                "event_id": event_id,
                "label": label,
                "node_id": node_name,
                "reviewed_at": datetime.now(timezone.utc).isoformat()
            })
            state_hash = compute_sha256(full_state)
            encrypted_state = encrypt_payload(full_state, config)
            
            cursor.execute("""
            INSERT OR IGNORE INTO cold_storage (hash, node_id, sealed_at, full_state)
            VALUES (?, ?, ?, ?);
            """, (state_hash, node_name, datetime.now(timezone.utc).isoformat(), encrypted_state))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Pool transition failed for {db_path}: {e}")

def load_events(config=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    evt_path = os.path.join(base_dir, EVENTS_FILE)
    if os.path.exists(evt_path):
        try:
            with open(evt_path, "r", encoding="utf-8") as f:
                events = json.load(f)
                # Decrypt details if encrypted
                for e in events:
                    if e.get("details") and isinstance(e["details"], str) and e["details"].startswith("enc:"):
                        e["details"] = decrypt_payload(e["details"], config)
                return events
        except Exception:
            return []
    return []

def save_events(events):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    evt_path = os.path.join(base_dir, EVENTS_FILE)
    with open(evt_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

def log_event(config, trigger_type, notification_title, media_files, details=""):
    events = load_events(config)
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
    events = load_events(config)
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

def insert_known_identity(identity_id, name, source, file_hash, local_path, metadata_dict, vector_list=None, config=None):
    """Stores a known identity and enrolls into both known_identities and Warm Pool."""
    init_sqlite_ledger(config)
    meta_str = json.dumps(metadata_dict) if isinstance(metadata_dict, dict) else str(metadata_dict)
    vec_str = json.dumps(vector_list) if vector_list else None
    
    for db_path in get_db_paths(config):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            # 1. Insert into known_identities
            cursor.execute("""
            INSERT OR REPLACE INTO known_identities (id, name, source, file_hash, local_path, metadata_json, vector_768)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (identity_id, name, source, file_hash, local_path, meta_str, vec_str))
            
            # 2. Also register into Warm Pool for training / triage context
            cursor.execute("""
            INSERT INTO warm_pool (node_id, timestamp, context_summary, metadata)
            VALUES (?, ?, ?, ?);
            """, (
                f"identity:{name}",
                datetime.now(timezone.utc).isoformat(),
                f"Enrolled Identity: {name} (source: {source}, hash: {file_hash[:12]}...)",
                json.dumps({
                    "identity_id": identity_id,
                    "name": name,
                    "source": source,
                    "file_hash": file_hash,
                    "local_path": local_path,
                    "has_vector": bool(vector_list)
                })
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[myCam SQLite Warning] Identity insert failed for {db_path}: {e}")

def get_known_identities(config=None):
    """Fetches all enrolled identities from the SQLite ledger."""
    init_sqlite_ledger(config)
    results = []
    primary_db = get_db_paths(config)[0]
    try:
        conn = sqlite3.connect(primary_db, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, source, file_hash, local_path, metadata_json, vector_768, created_at FROM known_identities ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        for r in rows:
            results.append({
                "id": r["id"],
                "name": r["name"],
                "source": r["source"],
                "file_hash": r["file_hash"],
                "local_path": r["local_path"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                "has_vector": bool(r["vector_768"]),
                "vector_768": json.loads(r["vector_768"]) if r["vector_768"] else None,
                "created_at": r["created_at"]
            })
        conn.close()
    except Exception as e:
        print(f"[myCam SQLite Warning] get_known_identities failed: {e}")
    return results
