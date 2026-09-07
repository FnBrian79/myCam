"""
photos_ingest.py - Sovereign Photo & Identity Harvester for myCam
===================================================================
Automatically discovers and connects designated photo libraries:
  - Google Takeout archives (E:\\takeout, NAS shares)
  - User Pictures directory (%USERPROFILE%\\Pictures)
  - Custom library locations

Extracts identity references, companion metadata (.supplemental-metad.json),
computes SHA-256 state hashes, generates local 768-d embeddings via BEAST's
Ollama (nomic-embed-text), and enrolls records directly into the 3-Tier
SQLite Warm Pool (mycam.db) with ZERO cloud leaks.
"""

import os
import sys
import json
import zipfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from storage import insert_known_identity, get_known_identities, get_storage_dir

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embeddings")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text:latest")

def get_designated_photo_sources(config=None):
    """Auto-discovers common, standard designated library locations with zero manual hunting."""
    sources = []
    
    # 1. Configured sources
    if config and "photo_sources" in config:
        for s in config["photo_sources"]:
            if os.path.exists(s):
                sources.append(os.path.abspath(s))
                
    # 2. Designated storage drives & Takeout archives
    known_takeout_dirs = [
        r"E:\takeout",
        r"T:\takeout",
        r"\\192.168.0.1\g\takeout",
        r"J:\takeout",
    ]
    for d in known_takeout_dirs:
        if os.path.exists(d):
            sources.append(d)

    # 3. Standard User Pictures directory
    user_pictures = os.path.expanduser(r"~\Pictures")
    if os.path.exists(user_pictures):
        sources.append(user_pictures)

    # 4. Local captures directory
    local_identities = os.path.join(get_storage_dir(config), "identities")
    os.makedirs(local_identities, exist_ok=True)
    sources.append(local_identities)

    # Deduplicate while preserving order
    return list(dict.fromkeys(sources))

def compute_file_sha256(filepath):
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def compute_bytes_sha256(data_bytes):
    """Computes SHA-256 hash of raw in-memory bytes."""
    return hashlib.sha256(data_bytes).hexdigest()

def get_local_embedding(text):
    """Generates 768-d embedding locally on BEAST via Ollama (zero cloud transmission)."""
    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("embedding", [])
    except Exception as e:
        # Graceful fallback if Ollama model is spinning up
        pass
    return None

def ingest_from_takeout_zip(zip_path, identities_dir, limit=50, config=None):
    """Scans a Takeout zip archive, selectively extracting Google Photos identities."""
    ingested_count = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()
            
            # Prioritize Profile pictures and people folders
            profile_photos = [n for n in namelist if "profile pictures" in n.lower() and any(n.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"])]
            other_photos = [n for n in namelist if "google photos" in n.lower() and any(n.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]) and n not in profile_photos]
            
            candidates = (profile_photos + other_photos)[:limit]
            
            for photo_entry in candidates:
                try:
                    # Read image bytes
                    img_bytes = z.read(photo_entry)
                    file_hash = compute_bytes_sha256(img_bytes)
                    ext = os.path.splitext(photo_entry)[1]
                    dest_filename = f"{file_hash[:16]}{ext}"
                    dest_path = os.path.join(identities_dir, dest_filename)
                    
                    # Save local copy if not already cached
                    if not os.path.exists(dest_path):
                        with open(dest_path, "wb") as f_out:
                            f_out.write(img_bytes)
                            
                    # Attempt to read companion metadata JSON
                    metadata = {}
                    companion_json = f"{photo_entry}.supplemental-metad.json"
                    companion_json_alt = f"{photo_entry}.json"
                    
                    for comp in [companion_json, companion_json_alt]:
                        if comp in namelist:
                            try:
                                raw_json = z.read(comp).decode("utf-8", errors="ignore")
                                metadata = json.loads(raw_json)
                                break
                            except Exception:
                                pass
                                
                    is_profile = "profile pictures" in photo_entry.lower()
                    name = "User Profile" if is_profile else os.path.basename(os.path.dirname(photo_entry))
                    
                    # Synthesize semantic text for local embedding
                    semantic_desc = f"Identity: {name} | Origin: Google Photos ({os.path.basename(zip_path)}) | Path: {photo_entry}"
                    if metadata.get("description"):
                        semantic_desc += f" | Description: {metadata['description']}"
                    if metadata.get("photoTakenTime", {}).get("formatted"):
                        semantic_desc += f" | Taken: {metadata['photoTakenTime']['formatted']}"
                        
                    vector = get_local_embedding(semantic_desc)
                    
                    identity_id = f"id_{file_hash[:12]}"
                    insert_known_identity(
                        identity_id=identity_id,
                        name=name,
                        source=f"takeout:{os.path.basename(zip_path)}",
                        file_hash=file_hash,
                        local_path=dest_path,
                        metadata_dict=metadata,
                        vector_list=vector,
                        config=config
                    )
                    ingested_count += 1
                except Exception as e:
                    print(f"[Takeout Ingest Warning] Failed on entry {photo_entry}: {e}")
    except Exception as e:
        print(f"[Takeout Ingest Warning] Failed opening zip {zip_path}: {e}")
        
    return ingested_count

def ingest_from_directory(dir_path, identities_dir, limit=50, config=None):
    """Scans a standard directory for photos and enrolls them into the identity registry."""
    ingested_count = 0
    supported_exts = {".jpg", ".jpeg", ".png", ".webp"}
    
    for root, _, files in os.walk(dir_path):
        for fname in files:
            if ingested_count >= limit:
                break
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported_exts:
                src_path = os.path.join(root, fname)
                try:
                    file_hash = compute_file_sha256(src_path)
                    name = Path(src_path).stem
                    semantic_desc = f"Local Photo Identity: {name} | Source Folder: {os.path.basename(root)}"
                    vector = get_local_embedding(semantic_desc)
                    
                    identity_id = f"id_{file_hash[:12]}"
                    insert_known_identity(
                        identity_id=identity_id,
                        name=name,
                        source=f"folder:{os.path.basename(dir_path)}",
                        file_hash=file_hash,
                        local_path=src_path,
                        metadata_dict={"filename": fname, "folder": root},
                        vector_list=vector,
                        config=config
                    )
                    ingested_count += 1
                except Exception as e:
                    print(f"[Photo Ingest Warning] Failed on {src_path}: {e}")
                    
    return ingested_count

def run_photo_ingest_pipeline(config=None, target_sources=None, limit_per_source=30):
    """Executes full zero-hunting auto-discovery and ingestion across all designated locations."""
    if not target_sources:
        target_sources = get_designated_photo_sources(config)
        
    identities_dir = os.path.join(get_storage_dir(config), "identities")
    os.makedirs(identities_dir, exist_ok=True)
    
    total_new = 0
    print("\n=======================================================")
    print(" 📸 myCam Sovereign Photo & Identity Harvester")
    print("=======================================================")
    print(f"Destination Vault: {identities_dir}")
    print(f"Designated Sources Found: {len(target_sources)}")
    for s in target_sources:
        print(f"  • {s}")
    print("=======================================================\n")
    
    for src in target_sources:
        if not os.path.exists(src):
            continue
            
        print(f"[*] Scanning Source: {src} ...")
        
        # Case A: Directory containing zip archives (like E:\takeout)
        if os.path.isdir(src):
            zips = [os.path.join(src, f) for f in os.listdir(src) if f.endswith(".zip")]
            if zips:
                for zpath in zips:
                    # Quick check if it's a Google Photos zip
                    try:
                        with zipfile.ZipFile(zpath, "r") as z:
                            if any("google photos" in n.lower() for n in z.namelist()[:60]):
                                print(f"  [+] Ingesting Google Photos archive: {os.path.basename(zpath)}")
                                count = ingest_from_takeout_zip(zpath, identities_dir, limit=limit_per_source, config=config)
                                total_new += count
                                print(f"      ➔ Enrolled {count} identities/vectors from archive.")
                    except Exception:
                        pass
            else:
                # Regular photo folder
                count = ingest_from_directory(src, identities_dir, limit=limit_per_source, config=config)
                total_new += count
                print(f"  ➔ Enrolled {count} photos from directory.")
                
        # Case B: Individual zip file
        elif src.endswith(".zip"):
            count = ingest_from_takeout_zip(src, identities_dir, limit=limit_per_source, config=config)
            total_new += count
            print(f"  ➔ Enrolled {count} identities from archive.")

    all_identities = get_known_identities(config)
    print("\n=======================================================")
    print(f"✅ Ingestion Complete. Total Enrolled Identities: {len(all_identities)}")
    print(f"📊 Newly Processed in this run: {total_new}")
    print("=======================================================\n")
    return all_identities

if __name__ == "__main__":
    from storage import init_sqlite_ledger
    init_sqlite_ledger()
    run_photo_ingest_pipeline()
