import os
import json
import time
import urllib.request
import urllib.parse
from threading import Thread
import pytest

from cleon_gate import evaluate_cleon_trip, CleonDynastyGate
from listener import start_webhook_server, check_adb_notifications

@pytest.fixture
def webhook_server(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_listener.db")
    monkeypatch.setenv("MYCAM_DB_PATH", test_db)
    monkeypatch.chdir(tmp_path)

    config = {
        "storage_dir": str(tmp_path / "captures"),
        "webhook_port": 8769,
        "bind_host": "127.0.0.1",
        "default_capture_mode": "snapshot",
        "alexa_bridge_enabled": False,
        "telegram": {"enabled": False}
    }

    t = Thread(target=start_webhook_server, args=(config,), daemon=True)
    t.start()
    time.sleep(0.5)
    return "http://127.0.0.1:8769"

def test_cleon_dynasty_gate(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_cleon.db")
    monkeypatch.setenv("MYCAM_DB_PATH", test_db)

    config = {"alexa_bridge_enabled": False, "telegram": {"enabled": False}}

    # Test Dawn noise filter
    res_noise = evaluate_cleon_trip("Unrelated text without keywords", config=config)
    assert res_noise["action_taken"] == "SUPPRESSED_BY_DAWN"

    # Test Day friendly match (contains valid signal keyword 'camera')
    res_friendly = evaluate_cleon_trip("Mom detected at Front Door Camera", config=config)
    assert res_friendly["action_taken"] in ["ACTIVE_DEFENSE_TRIGGERED", "SEALED_SILENT_GOLD"]

    # Test Dusk unknown visitor defense
    res_unknown = evaluate_cleon_trip("Motion detected on Floodlight", config=config)
    assert res_unknown["action_taken"] == "ACTIVE_DEFENSE_TRIGGERED"

def test_listener_endpoints(webhook_server):
    # 1. GET /dashboard
    req = urllib.request.Request(f"{webhook_server}/dashboard")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "myCam" in html

    # 2. POST /trigger
    post_data = json.dumps({"title": "Test Doorbell Motion", "mode": "snapshot"}).encode("utf-8")
    req = urllib.request.Request(f"{webhook_server}/trigger", data=post_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "triggered"

    # 3. GET /api/events
    req = urllib.request.Request(f"{webhook_server}/api/events")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        events = json.loads(resp.read().decode("utf-8"))
        assert isinstance(events, list)

    # 4. GET /api/identities
    req = urllib.request.Request(f"{webhook_server}/api/identities")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        identities = json.loads(resp.read().decode("utf-8"))
        assert isinstance(identities, list)

    # 5. GET /api/sources
    req = urllib.request.Request(f"{webhook_server}/api/sources")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        sources_data = json.loads(resp.read().decode("utf-8"))
        assert "sources" in sources_data
