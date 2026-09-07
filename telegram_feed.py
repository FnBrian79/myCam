import json
import os
import urllib.request
import urllib.parse
from storage import update_training_label

def get_telegram_config(config):
    tg = config.get("telegram", {})
    token = tg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = tg.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
    enabled = tg.get("enabled", False)
    return enabled, token, chat_id, tg

def send_telegram_alert(config, event_id, title, media_path=None, details=""):
    """
    Asynchronously delivers a rich media alert with inline training buttons to Telegram.
    Allows user to classify events (Person, Vehicle, Animal, False Alarm) directly from chat/smartwatch.
    """
    enabled, token, chat_id, tg_opts = get_telegram_config(config)
    if not enabled or not token or not chat_id:
        return False

    training_mode = tg_opts.get("training_mode", True)
    
    caption = f"📹 <b>myCam Sentinel</b>\n\n<b>Alert:</b> {title}\n<b>Event ID:</b> <code>{event_id}</code>\n"
    if details:
        caption += f"<b>Details:</b> {details}\n"

    reply_markup = None
    if training_mode:
        caption += "\n🎯 <i>Tap to classify for AI training:</i>"
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "👤 Person", "callback_data": f"lbl:{event_id}:person"},
                    {"text": "🚗 Vehicle", "callback_data": f"lbl:{event_id}:vehicle"}
                ],
                [
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
            if reply_markup:
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
                "parse_mode": "HTML"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
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
    """Parses incoming callback queries from inline buttons and records training labels."""
    # Format: lbl:<event_id>:<label>
    try:
        parts = callback_data.split(":")
        if len(parts) >= 3 and parts[0] == "lbl":
            event_id = parts[1]
            label = parts[2]
            update_training_label(event_id, label, config)
            print(f"[myCam Training Ground Truth] Labeled {event_id} as '{label}'")
            return True, f"Logged as {label}"
    except Exception as e:
        print(f"[myCam Telegram Callback Error] {e}")
    return False, "Error"
