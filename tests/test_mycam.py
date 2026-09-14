import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
import threading
import requests

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vault_crypto import encrypt_payload, decrypt_payload, compute_sha256, get_or_create_key
from storage import (
    get_storage_dir, init_sqlite_ledger, write_to_sqlite,
    log_event, load_events, save_events, cleanup_old_media,
    insert_known_identity, get_known_identities, update_training_label
)
from cleon_gate import CleonDynastyGate, evaluate_cleon_trip
from listener import WebhookHandler
from photos_ingest import get_designated_photo_sources, ingest_from_directory
from video import compile_frames_to_animation

class TestVaultCrypto(unittest.TestCase):
    def test_sha256(self):
        h = compute_sha256("test_string")
        self.assertEqual(len(h), 64)

    def test_encryption_disabled(self):
        cfg = {"encryption_enabled": False}
        payload = "plain_text"
        self.assertEqual(encrypt_payload(payload, cfg), "plain_text")
        self.assertEqual(decrypt_payload(payload, cfg), "plain_text")

    def test_encryption_enabled(self):
        cfg = {"encryption_enabled": True}
        payload = '{"test": "data"}'
        enc = encrypt_payload(payload, cfg)
        self.assertTrue(enc.startswith("enc:"))
        dec = decrypt_payload(enc, cfg)
        self.assertEqual(dec, payload)

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_mycam.db")
        self.patcher = patch.dict(os.environ, {"MYCAM_DB_PATH": self.db_path})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_init_and_identity(self):
        cfg = {"storage_dir": self.temp_dir.name}
        init_sqlite_ledger(cfg)
        self.assertTrue(os.path.exists(self.db_path))

        insert_known_identity("id_001", "Alice", "test_src", "hash123", "/path/alice.jpg", {"role": "family"}, [0.1]*768, cfg)
        identities = get_known_identities(cfg)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0]["name"], "Alice")

    def test_log_event_and_label_update(self):
        cfg = {"storage_dir": self.temp_dir.name}
        evt = log_event(cfg, "test_trigger", "Motion Detected", [])
        self.assertIsNotNone(evt.get("id"))

        update_training_label(evt["id"], "APPROVED_KNOWN", cfg)

class TestCleonGate(unittest.TestCase):
    def test_dawn_gate_noise_rejection(self):
        gate = CleonDynastyGate()
        res = gate.evaluate_trip("Random noise string without keyword")
        self.assertEqual(res["action_taken"], "SUPPRESSED_BY_DAWN")
        self.assertFalse(res["gate_1_dawn"]["passed"])

    def test_day_and_dusk_friendly(self):
        cfg = {"friendly_names": ["Mom"], "alexa_bridge_enabled": False}
        res = evaluate_cleon_trip("Mom arriving at front door motion alert", config=cfg)
        self.assertEqual(res["gate_2_day"]["classification"], "FRIENDLY_VERIFIED")
        self.assertEqual(res["action_taken"], "SEALED_SILENT_GOLD")

    def test_day_and_dusk_unrecognized(self):
        cfg = {"alexa_bridge_enabled": False}
        with patch("cleon_gate.send_telegram_alert", return_value=True):
            res = evaluate_cleon_trip("Motion detected on backyard camera alert", config=cfg)
            self.assertEqual(res["gate_2_day"]["classification"], "UNRECOGNIZED_ANOMALY")
            self.assertEqual(res["action_taken"], "ACTIVE_DEFENSE_TRIGGERED")

class TestListenerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18765
        cls.config = {"bind_host": "127.0.0.1", "webhook_port": cls.port}
        WebhookHandler.config = cls.config
        cls.server = HTTPServer(("127.0.0.1", cls.port), WebhookHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_dashboard_endpoint(self):
        resp = requests.get(f"http://127.0.0.1:{self.port}/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("myCam Sentinel", resp.text)

    def test_events_api(self):
        resp = requests.get(f"http://127.0.0.1:{self.port}/api/events")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_trigger_api(self):
        resp = requests.post(f"http://127.0.0.1:{self.port}/trigger", json={"title": "Test Camera Trigger", "mode": "snapshot"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "triggered")

class TestPhotosIngest(unittest.TestCase):
    def test_get_sources(self):
        sources = get_designated_photo_sources({"photo_sources": ["/tmp"]})
        self.assertIn("/tmp", sources)

class TestVideo(unittest.TestCase):
    def test_compile_frames_empty(self):
        res = compile_frames_to_animation("/non_existent_folder_xyz")
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
