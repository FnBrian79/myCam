import os
import pytest
from vault_crypto import get_or_create_key, encrypt_payload, decrypt_payload, compute_sha256

def test_compute_sha256():
    data = "hello world"
    # echo -n "hello world" | sha256sum -> b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert compute_sha256(data) == expected

def test_get_or_create_key():
    config = {"encryption_key": "custom_key_123"}
    assert get_or_create_key(config) == "custom_key_123"

def test_encrypt_decrypt_payload(tmp_path):
    config = {
        "encryption_enabled": True,
        "encryption_key": "12345678901234567890123456789012" # 32 chars urlsafe
    }
    # Create fernet compliant key
    import base64
    raw_key = base64.urlsafe_b64encode(b"01234567890123456789012345678901").decode("utf-8")
    config["encryption_key"] = raw_key

    original_text = "Sensitive myCam Sentinel Payload"
    encrypted = encrypt_payload(original_text, config)
    assert encrypted.startswith("enc:")
    assert encrypted != original_text

    decrypted = decrypt_payload(encrypted, config)
    assert decrypted == original_text

def test_encrypt_disabled():
    config = {"encryption_enabled": False}
    original_text = "Plaintext Payload"
    assert encrypt_payload(original_text, config) == original_text
    assert decrypt_payload(original_text, config) == original_text
