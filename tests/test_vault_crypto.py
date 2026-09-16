import os
import pytest
import base64
from vault_crypto import compute_sha256, get_or_create_key, encrypt_payload, decrypt_payload

def test_compute_sha256():
    data = "mycam_sovereign_sentinel_test"
    digest = compute_sha256(data)
    assert isinstance(digest, str)
    assert len(digest) == 64
    assert compute_sha256(data) == digest

def test_get_or_create_key_env(monkeypatch):
    test_key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    monkeypatch.setenv("SOVEREIGN_ENCRYPTION_KEY", test_key)
    assert get_or_create_key() == test_key

def test_get_or_create_key_config():
    test_key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    config = {"encryption_key": test_key}
    assert get_or_create_key(config) == test_key

def test_payload_encryption_disabled():
    data = "sample_unencrypted_data"
    config = {"encryption_enabled": False}
    encrypted = encrypt_payload(data, config)
    assert encrypted == data
    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == data

def test_payload_encryption_enabled():
    test_key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    config = {"encryption_enabled": True, "encryption_key": test_key}
    data = "sensitive_sentinel_log_data"

    encrypted = encrypt_payload(data, config)
    assert encrypted.startswith("enc:")
    assert encrypted != data

    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == data
