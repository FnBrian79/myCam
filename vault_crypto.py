import os
import base64
import hashlib

def get_or_create_key(config=None):
    """
    Retrieves or generates a 256-bit sovereign encryption key.
    Key priority:
    1. SOVEREIGN_ENCRYPTION_KEY environment variable
    2. Config file "encryption_key"
    3. Local .vault.key file (auto-generated if missing and encryption enabled)
    """
    env_key = os.environ.get("SOVEREIGN_ENCRYPTION_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
        
    if config and config.get("encryption_key") and str(config["encryption_key"]).strip():
        return str(config["encryption_key"]).strip()
        
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".vault.key")
    if os.path.exists(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass

    # Auto-generate a secure URL-safe base64 key
    new_key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    try:
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key

def encrypt_payload(data_str: str, config=None) -> str:
    """Encrypts a plaintext string (JSON or metadata) using Fernet AES-128-CBC + HMAC."""
    if not (config and config.get("encryption_enabled", False)):
        return data_str

    try:
        from cryptography.fernet import Fernet
        key = get_or_create_key(config)
        fernet = Fernet(key.encode('utf-8'))
        encrypted_bytes = fernet.encrypt(data_str.encode('utf-8'))
        return "enc:" + encrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"[Vault Crypto Warning] Encryption fallback: {e}")
        return data_str

def decrypt_payload(enc_str: str, config=None) -> str:
    """Decrypts a previously encrypted payload string."""
    if not enc_str or not isinstance(enc_str, str) or not enc_str.startswith("enc:"):
        return enc_str

    try:
        from cryptography.fernet import Fernet
        key = get_or_create_key(config)
        fernet = Fernet(key.encode('utf-8'))
        raw_token = enc_str[4:].encode('utf-8')
        decrypted_bytes = fernet.decrypt(raw_token)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"[Vault Crypto Warning] Decryption failed: {e}")
        return enc_str

def compute_sha256(content: str) -> str:
    """Computes SHA-256 hash for immutable cold-pool sealing."""
    if content is None:
        content = ""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
