import pytest
from telegram_feed import get_telegram_config, handle_telegram_callback

def test_get_telegram_config(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    config = {
        "telegram": {
            "enabled": True,
            "bot_token": "12345:ABCDE",
            "chat_id": "98765"
        }
    }
    enabled, token, chat_id, tg = get_telegram_config(config)
    assert enabled is True
    assert token == "12345:ABCDE"
    assert chat_id == "98765"

def test_handle_telegram_callback(monkeypatch):
    monkeypatch.setattr("telegram_feed.update_training_label", lambda event_id, label, config=None: None)

    success, feedback = handle_telegram_callback("act:evt_100:approve")
    assert success is True
    assert "Approved" in feedback

    success, feedback = handle_telegram_callback("act:evt_100:deny")
    assert success is True
    assert "Denied" in feedback

    success, feedback = handle_telegram_callback("lbl:evt_100:person")
    assert success is True
    assert "person" in feedback
