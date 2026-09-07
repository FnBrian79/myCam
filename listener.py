import time
import json
import os
import urllib.parse
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from recorder import capture_screenshot, capture_sequence
from recorder_adb import record_adb_stream, check_adb_connected, resolve_adb_cmd, get_adb_prefix, ensure_device_ready, CREATE_NO_WINDOW
from storage import log_event, load_events
from dashboard import DASHBOARD_HTML
from telegram_feed import send_telegram_alert, handle_telegram_callback, start_telegram_polling

SEEN_NOTIFICATIONS = set()

def dispatch_phone_alert(title, details, config, media_path=None, event_id=""):
    """Dispatches notifications via Telegram (for training/review) and ntfy push."""
    # 1. Telegram Asynchronous Training & Review Feed
    try:
        send_telegram_alert(config, event_id, title, media_path, details)
    except Exception as e:
        print(f"[myCam Alert Warning] Telegram dispatch error: {e}")

    # 2. ntfy push channel (optional)
    ntfy_topic = config.get("ntfy_topic")
    if ntfy_topic:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://ntfy.sh/{ntfy_topic}",
                data=f"{title}\n{details}".encode("utf-8"),
                headers={"Title": title.encode("utf-8"), "Priority": "default"}
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

    # 3. Native ADB push notification if edge device is attached
    try:
        adb_cmd = resolve_adb_cmd(config)
        if check_adb_connected(config):
            clean_title = title.replace('"', '')
            clean_msg = details.replace('"', '')
            subprocess.run(
                [adb_cmd, "shell", "cmd", "notification", "post", "-S", "bigtext", "-t", clean_title, "sovereign_alert", clean_msg],
                capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW
            )
    except Exception:
        pass

class WebhookHandler(BaseHTTPRequestHandler):
    config = {}

    def log_message(self, format, *args):
        # Suppress routine console spam for silent daemon operation
        pass

    def do_POST(self):
        if self.path == '/trigger' or self.path == '/':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {"raw": body}
                
            title = data.get("title", data.get("message", "Incoming Camera Trigger"))
            mode = data.get("mode", self.config.get("default_capture_mode", "hybrid"))
            
            print(f"[myCam Sentinel] Trigger received: '{title}' (mode: {mode})")
            
            media_result = None
            event_id = f"evt_{int(time.time())}"
            if "ring" in title.lower() or mode == "adb" or mode == "ring":
                duration = self.config.get("adb_record_duration", 15)
                Thread(target=self._record_and_dispatch, args=(duration, title, event_id)).start()
            elif mode == "snapshot":
                media_result = capture_screenshot(self.config, title=title)
                log_event(self.config, "webhook_snapshot", title, [media_result] if media_result else [])
                dispatch_phone_alert(title, "Snapshot captured by myCam", self.config, media_path=media_result, event_id=event_id)
            else:
                Thread(target=capture_sequence, args=(self.config, 5, 10, title)).start()
                dispatch_phone_alert(title, f"Sequence captured ({mode} mode)", self.config, event_id=event_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "triggered", "title": title, "event_id": event_id})
            self.wfile.write(response.encode('utf-8'))

        elif self.path == '/api/telegram_webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                update = json.loads(body)
                if "callback_query" in update:
                    cb_data = update["callback_query"].get("data", "")
                    handle_telegram_callback(cb_data, self.config)
            except Exception as e:
                print(f"[myCam Webhook Error] {e}")

            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _record_and_dispatch(self, duration, title, event_id):
        media_path = record_adb_stream(self.config, duration_sec=duration, title=title)
        dispatch_phone_alert(title, "Live edge motion captured and vaulted.", self.config, media_path=media_path, event_id=event_id)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == '/dashboard' or parsed_url.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
            
        elif parsed_url.path == '/api/events':
            events = load_events()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(events).encode('utf-8'))
            
        elif parsed_url.path == '/api/media':
            query = urllib.parse.parse_qs(parsed_url.query)
            file_path = query.get('path', [None])[0]
            if file_path:
                if not os.path.isabs(file_path):
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    file_path = os.path.normpath(os.path.join(base_dir, file_path))
                if os.path.exists(file_path):
                    self.send_response(200)
                    if file_path.lower().endswith('.png') or file_path.lower().endswith('.jpg'):
                        self.send_header('Content-Type', 'image/png')
                    elif file_path.lower().endswith('.mp4'):
                        self.send_header('Content-Type', 'video/mp4')
                    else:
                        self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def start_webhook_server(config):
    bind_host = config.get("bind_host", "127.0.0.1")
    port = config.get("webhook_port", 8765)
    WebhookHandler.config = config
    server = HTTPServer((bind_host, port), WebhookHandler)
    is_loopback = bind_host in ("127.0.0.1", "localhost")
    print(f"[myCam] Sentinel Server live on http://{bind_host}:{port}/dashboard (Local Loopback Only: {is_loopback})")
    server.serve_forever()

def check_adb_notifications(config):
    global SEEN_NOTIFICATIONS
    keywords = config.get("target_keywords", ["ring", "motion", "camera", "doorbell", "floodlight"])
    target_pkg = config.get("ring_package_name", "com.ringapp").lower()
    try:
        prefix = get_adb_prefix(config)
        res = subprocess.run(
            prefix + ["shell", "dumpsys", "notification", "--noredact"],
            capture_output=True, timeout=4, creationflags=CREATE_NO_WINDOW
        )
        if res.returncode == 0:
            stdout_text = res.stdout.decode("utf-8", errors="replace")
            current_active_keys = set()
            for line in stdout_text.splitlines():
                line_clean = line.strip()
                if "NotificationRecord(" in line_clean:
                    lower_line = line_clean.lower()
                    key = None
                    if "key=" in line_clean:
                        key = line_clean.split("key=")[1].split()[0]
                    else:
                        key = line_clean
                    current_active_keys.add(key)
                    
                    is_target_app = (f"pkg={target_pkg}" in lower_line or target_pkg in lower_line)
                    has_keyword = any(kw in lower_line for kw in keywords)
                    
                    if (is_target_app or has_keyword) and (key not in SEEN_NOTIFICATIONS):
                        SEEN_NOTIFICATIONS.add(key)
                        matched = "Ring Motion" if is_target_app else "Camera Motion"
                        for kw in keywords:
                            if kw in lower_line:
                                matched = kw.capitalize()
                                break
                        print(f"[myCam ADB Silent Poll] NEW alert: {matched} (Key: {key[:30]}...)")
                        return matched
            if len(SEEN_NOTIFICATIONS) > 300:
                SEEN_NOTIFICATIONS &= current_active_keys
    except Exception:
        pass
    return None

def run_listener_daemon(config):
    print("[myCam Daemon] Initializing continuous sovereign sentinel...")
    
    # Launch Telegram interactive polling (Approve / Deny)
    start_telegram_polling(config)
    
    t = Thread(target=start_webhook_server, args=(config,), daemon=True)
    t.start()
    
    last_adb_trigger = 0
    was_connected = False
    try:
        while True:
            is_connected = check_adb_connected(config)
            if is_connected and not was_connected:
                was_connected = True
                print("[myCam Sentinel] Edge device connected! Running post-boot auto-recovery...")
                ensure_device_ready(config)
            elif not is_connected and was_connected:
                was_connected = False
                print("[myCam Sentinel] Device offline / rebooting. Entering silent poll mode...")
            now = time.time()
            if now - last_adb_trigger > 15:
                adb_match = check_adb_notifications(config)
                if adb_match:
                    last_adb_trigger = now
                    event_id = f"evt_{int(now)}"
                    title = f"Camera Alert: {adb_match.upper()}"
                    
                    if check_adb_connected(config):
                        duration = config.get("adb_record_duration", 15)
                        media_file = record_adb_stream(config, duration_sec=duration, title=title)
                    else:
                        try:
                            media_file = capture_screenshot(config, title=title)
                            if media_file:
                                log_event(config, "gdi_motion_snapshot", title, [media_file])
                        except Exception:
                            media_file = None
                            
                    dispatch_phone_alert(title, "Live motion captured and vaulted to sovereign storage.", config, media_path=media_file, event_id=event_id)
            time.sleep(3)
    except KeyboardInterrupt:
        print("[myCam Daemon] Daemon stopped gracefully.")
