import json
import os
import time
import urllib.request
import urllib.parse
from threading import Thread
from storage import update_training_label

def get_telegram_config(config):
    tg = config.get("telegram", {})
    token = tg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = tg.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
    enabled = tg.get("enabled", False)
    return enabled, token, chat_id, tg

def send_telegram_alert(config, event_id, title, media_path=None, details=""):
    """
    Asynchronously delivers a rich media alert to Telegram with Approve / Deny and classification buttons.
    Operates 100% locally from the background daemon.
    """
    if isinstance(media_path, list):
        media_path = media_path[-1] if media_path else None

    enabled, token, chat_id, tg_opts = get_telegram_config(config)
    if not enabled or not token or not chat_id:
        return False

    caption = (
        f"🛡️ <b>myCam Sovereign Sentinel</b>\n\n"
        f"<b>Alert:</b> {title}\n"
        f"<b>Event ID:</b> <code>{event_id}</code>\n"
    )
    if details:
        caption += f"<b>Details:</b> {details}\n"

    caption += "\n👇 <b>Verify visitor / target:</b>"
    
    # 2-Row Interactive Keyboard: Action (Approve/Deny) + Category (Person/Animal)
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve (Known / OK)", "callback_data": f"act:{event_id}:approve"},
                {"text": "❌ Deny (Intruder / Alert)", "callback_data": f"act:{event_id}:deny"}
            ],
            [
                {"text": "👤 Person", "callback_data": f"lbl:{event_id}:person"},
                {"text": "🐾 Animal", "callback_data": f"lbl:{event_id}:animal"},
                {"text": "🍃 False Alarm", "callback_data": f"lbl:{event_id}:false_alarm"}
            ]
        ]
    }

    try:
        if media_path and os.path.exists(media_path):
            is_video = media_path.lower().endswith(".mp4")
            endpoint = "sendVideo" if is_video else "sendPhoto"
            field_name = "video" if is_video else "photo"
            
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = bytearray()
            
            # Form field: chat_id
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode('utf-8'))
            
            # Form field: parse_mode
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend('Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode('utf-8'))
            
            # Form field: caption
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode('utf-8'))
            
            # Form field: reply_markup
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="reply_markup"\r\n\r\n{json.dumps(reply_markup)}\r\n'.encode('utf-8'))
            
            # File data
            filename = os.path.basename(media_path)
            content_type = "video/mp4" if is_video else "image/png"
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode('utf-8'))
            body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8'))
            with open(media_path, "rb") as f:
                body.extend(f.read())
            body.extend(f"\r\n--{boundary}--\r\n".encode('utf-8'))
            
            req_url = f"https://api.telegram.org/bot{token}/{endpoint}"
            req = urllib.request.Request(
                req_url,
                data=bytes(body),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status == 200
        else:
            # Fallback text message
            payload = {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.status == 200
    except Exception as e:
        print(f"[myCam Telegram Warning] Failed to send alert: {e}")
        return False

def handle_telegram_callback(callback_data, config=None):
    """Parses incoming callback queries from inline buttons and records user decisions."""
    try:
        parts = callback_data.split(":")
        if len(parts) >= 3:
            action_type = parts[0]
            event_id = parts[1]
            action = parts[2]
            
            if action_type == "act":
                if action == "approve":
                    update_training_label(event_id, "APPROVED_KNOWN", config)
                    print(f"[myCam Triage] Event {event_id} APPROVED by user.")
                    return True, "✅ Approved (Saved to Warm Pool)"
                elif action == "deny":
                    update_training_label(event_id, "DENIED_INTRUDER", config)
                    print(f"[myCam Triage] Event {event_id} DENIED by user. Flagged as perimeter alert!")
                    return True, "🚨 Denied (Perimeter Alert Flagged)"
                    
            elif action_type == "lbl":
                update_training_label(event_id, action, config)
                print(f"[myCam Training Ground Truth] Labeled {event_id} as '{action}'")
                return True, f"Logged as {action}"
    except Exception as e:
        print(f"[myCam Telegram Callback Error] {e}")
    return False, "Error processing decision"

def start_telegram_polling(config):
    """
    Background long-polling loop for Telegram button callbacks.
    100% outbound HTTPS polling — zero incoming ports, zero public webhooks needed.
    """
    enabled, token, _, _ = get_telegram_config(config)
    if not enabled or not token:
        return

    def _poll():
        print("[myCam Telegram] Long-polling thread active for interactive Approve/Deny buttons...")
        offset = 0
        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=20"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            cb_data = cb.get("data", "")
                            
                            success, feedback = handle_telegram_callback(cb_data, config)
                            
                            # Acknowledge button click so Telegram stops spinner
                            try:
                                ans_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                                ans_payload = json.dumps({"callback_query_id": cb_id, "text": feedback}).encode("utf-8")
                                ans_req = urllib.request.Request(ans_url, data=ans_payload, headers={"Content-Type": "application/json"})
                                urllib.request.urlopen(ans_req, timeout=5)
                            except Exception:
                                pass
            except Exception:
                time.sleep(5)

    t = Thread(target=_poll, daemon=True)
    t.start()
