import pytest
from telegram_feed import get_telegram_config, handle_telegram_callback

def test_get_telegram_config_default():
    config = {}
    enabled, token, chat_id, tg_opts = get_telegram_config(config)
    assert enabled is False

def test_get_telegram_config_configured(monkeypatch):
    config = {
        "telegram": {
            "enabled": True,
            "bot_token": "12345:ABCDEF",
            "chat_id": "987654321"
        }
    }
    enabled, token, chat_id, tg_opts = get_telegram_config(config)
    assert enabled is True
    assert token == "12345:ABCDEF"
    assert chat_id == "987654321"

def test_handle_telegram_callback(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_tg.db")
    monkeypatch.setenv("MYCAM_DB_PATH", db_file)
    config = {"storage_dir": str(tmp_path / "captures")}

    # Test Approve Callback
    success, msg = handle_telegram_callback("act:evt_101:approve", config=config)
    assert success is True
    assert "Approved" in msg

    # Test Deny Callback
    success, msg = handle_telegram_callback("act:evt_101:deny", config=config)
    assert success is True
    assert "Denied" in msg

    # Test Label Callback
    success, msg = handle_telegram_callback("lbl:evt_101:person", config=config)
    assert success is True
    assert "person" in msg

    # Test Invalid Callback
    success, msg = handle_telegram_callback("invalid_format", config=config)
    assert success is False
