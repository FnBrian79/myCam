import pytest
from unittest.mock import patch, MagicMock
from telegram_feed import get_telegram_config, handle_telegram_callback, send_telegram_alert

def test_get_telegram_config():
    config = {
        "telegram": {
            "enabled": True,
            "bot_token": "test_token_123",
            "chat_id": "test_chat_456"
        }
    }
    enabled, token, chat_id, tg_opts = get_telegram_config(config)
    assert enabled is True
    assert token == "test_token_123"
    assert chat_id == "test_chat_456"

def test_handle_telegram_callback_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCAM_DB_PATH", str(tmp_path / "tg_test.db"))

    cb_data = "act:evt_1001:approve"
    success, msg = handle_telegram_callback(cb_data)
    assert success is True
    assert "Approved" in msg

def test_handle_telegram_callback_deny(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCAM_DB_PATH", str(tmp_path / "tg_test.db"))

    cb_data = "act:evt_1002:deny"
    success, msg = handle_telegram_callback(cb_data)
    assert success is True
    assert "Denied" in msg

def test_handle_telegram_callback_label(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCAM_DB_PATH", str(tmp_path / "tg_test.db"))

    cb_data = "lbl:evt_1003:person"
    success, msg = handle_telegram_callback(cb_data)
    assert success is True
    assert "person" in msg

def test_send_telegram_alert_disabled():
    config = {"telegram": {"enabled": False}}
    assert send_telegram_alert(config, "evt_1", "Test Alert") is False
