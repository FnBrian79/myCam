import os
import tempfile
import unittest
import shutil
import json
from PIL import Image

import vault_crypto
import storage
import cleon_gate
import video
import photos_ingest
import recorder_adb
import recorder

class TestVaultCrypto(unittest.TestCase):
    def test_key_generation(self):
        config = {"encryption_key": "custom_test_key_12345"}
        key = vault_crypto.get_or_create_key(config)
        self.assertEqual(key, "custom_test_key_12345")

    def test_encrypt_decrypt_payload(self):
        config = {"encryption_enabled": True}
        raw_text = "Sensitive myCam Sentinel Telemetry Data"
        encrypted = vault_crypto.encrypt_payload(raw_text, config)
        self.assertTrue(encrypted.startswith("enc:"))

        decrypted = vault_crypto.decrypt_payload(encrypted, config)
        self.assertEqual(decrypted, raw_text)

    def test_encryption_disabled_pass_through(self):
        config = {"encryption_enabled": False}
        raw_text = "Plaintext Data"
        result = vault_crypto.encrypt_payload(raw_text, config)
        self.assertEqual(result, raw_text)

    def test_compute_sha256(self):
        sample = "hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        self.assertEqual(vault_crypto.compute_sha256(sample), expected)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_mycam.db")
        os.environ["MYCAM_DB_PATH"] = self.db_path
        self.config = {
            "storage_dir": self.temp_dir,
            "encryption_enabled": False
        }

    def tearDown(self):
        if "MYCAM_DB_PATH" in os.environ:
            del os.environ["MYCAM_DB_PATH"]
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sqlite_ledger_init_and_write(self):
        storage.init_sqlite_ledger(self.config)
        self.assertTrue(os.path.exists(self.db_path))

        event_id = "evt_test_123"
        storage.write_to_sqlite(
            event_id=event_id,
            source="Test_Source",
            event_type="motion",
            payload={"test": "data"},
            config=self.config
        )

    def test_update_training_label_3tier_promotion(self):
        storage.init_sqlite_ledger(self.config)
        event_id = "evt_promote_1"
        storage.write_to_sqlite(
            event_id=event_id,
            source="Test_Source",
            event_type="motion",
            payload={"test": "data"},
            config=self.config
        )
        storage.update_training_label(event_id, "APPROVED_KNOWN", self.config)

    def test_identity_registration_and_retrieval(self):
        storage.init_sqlite_ledger(self.config)
        storage.insert_known_identity(
            identity_id="id_001",
            name="Alice",
            source="test_folder",
            file_hash="hash_1234567890",
            local_path="/tmp/alice.jpg",
            metadata_dict={"tag": "family"},
            vector_list=[0.1] * 768,
            config=self.config
        )
        identities = storage.get_known_identities(self.config)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0]["name"], "Alice")
        self.assertTrue(identities[0]["has_vector"])


class TestCleonGate(unittest.TestCase):
    def test_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cleon_gate.cosine_similarity(v1, v2), 1.0)

        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cleon_gate.cosine_similarity(v1, v3), 0.0)

    def test_dawn_gate_rejection(self):
        gate = cleon_gate.CleonDynastyGate()
        res = gate.evaluate_trip("Unrelated System Log")
        self.assertEqual(res["action_taken"], "SUPPRESSED_BY_DAWN")
        self.assertFalse(res["gate_1_dawn"]["passed"])

    def test_dawn_gate_acceptance(self):
        gate = cleon_gate.CleonDynastyGate()
        res = gate.evaluate_trip("Front Door Motion Detected")
        self.assertTrue(res["gate_1_dawn"]["passed"])


class TestVideoCompilation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compile_gif_fallback(self):
        # Create 3 small test PNG frames
        for i in range(3):
            img = Image.new("RGB", (100, 100), color=(i * 50, 100, 100))
            img.save(os.path.join(self.temp_dir, f"frame_{i:04d}.png"))

        result = video.compile_frames_to_animation(self.temp_dir, output_format="gif", fps=5)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))


class TestPhotosIngest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("myCam Sentinel Test File")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compute_file_sha256(self):
        file_hash = photos_ingest.compute_file_sha256(self.test_file)
        bytes_hash = photos_ingest.compute_bytes_sha256(b"myCam Sentinel Test File")
        self.assertEqual(file_hash, bytes_hash)

    def test_get_designated_photo_sources(self):
        sources = photos_ingest.get_designated_photo_sources()
        self.assertIsInstance(sources, list)


class TestRecorderADB(unittest.TestCase):
    def test_resolve_adb_cmd(self):
        adb_cmd = recorder_adb.resolve_adb_cmd()
        self.assertIsNotNone(adb_cmd)

    def test_recorder_snapshot_run(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = {"storage_dir": temp_dir}
            snap_path = recorder.capture_screenshot(config, title="Unit Test Snapshot")
            if snap_path:
                self.assertTrue(os.path.exists(snap_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
