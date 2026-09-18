import json
import urllib.request
import urllib.parse
import pytest
from threading import Thread
import time
from listener import start_webhook_server

@pytest.fixture(scope="module")
def server_url(tmp_path_factory):
    storage_dir = str(tmp_path_factory.mktemp("captures"))
    port = 8799
    config = {
        "webhook_port": port,
        "bind_host": "127.0.0.1",
        "storage_dir": storage_dir,
        "default_capture_mode": "snapshot"
    }

    t = Thread(target=start_webhook_server, args=(config,), daemon=True)
    t.start()
    time.sleep(0.5)
    return f"http://127.0.0.1:{port}"

def test_dashboard_endpoint(server_url):
    req = urllib.request.Request(f"{server_url}/dashboard")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "myCam Sentinel" in html

def test_api_events_endpoint(server_url):
    req = urllib.request.Request(f"{server_url}/api/events")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, list)

def test_post_trigger_endpoint(server_url):
    payload = json.dumps({"title": "Test Webhook Trigger", "mode": "snapshot"}).encode("utf-8")
    req = urllib.request.Request(
        f"{server_url}/trigger",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "triggered"
        assert data["title"] == "Test Webhook Trigger"
