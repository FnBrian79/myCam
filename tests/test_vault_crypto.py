import os
import pytest
from vault_crypto import get_or_create_key, encrypt_payload, decrypt_payload, compute_sha256

def test_get_or_create_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SOVEREIGN_ENCRYPTION_KEY", raising=False)
    config = {}
    key = get_or_create_key(config)
    assert isinstance(key, str)
    assert len(key) > 0

    # Explicit key in config
    config = {"encryption_key": "my_custom_secret_key"}
    assert get_or_create_key(config) == "my_custom_secret_key"

    # Explicit key in env var
    monkeypatch.setenv("SOVEREIGN_ENCRYPTION_KEY", "env_secret_key")
    assert get_or_create_key(config) == "env_secret_key"

def test_encrypt_decrypt_payload():
    config = {"encryption_enabled": True}
    original_text = "Secret camera event data"

    encrypted = encrypt_payload(original_text, config)
    assert encrypted != original_text
    assert encrypted.startswith("enc:")

    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == original_text

def test_encrypt_disabled():
    config = {"encryption_enabled": False}
    original_text = "Plain text camera event"

    result = encrypt_payload(original_text, config)
    assert result == original_text

def test_compute_sha256():
    data = "myCam Event SHA256 Verification"
    hash_val = compute_sha256(data)
    assert len(hash_val) == 64
    assert hash_val == compute_sha256(data)
