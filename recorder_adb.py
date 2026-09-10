import subprocess
import time
import os
import shutil
from datetime import datetime
from storage import log_event

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def resolve_adb_cmd(config=None):
    """Dynamically resolves the ADB binary path across OS platforms."""
    if config and config.get("adb_binary_path") and os.path.exists(config["adb_binary_path"]):
        return config["adb_binary_path"]
        
    env_adb = os.environ.get("ADB_PATH")
    if env_adb and os.path.exists(env_adb):
        return env_adb
        
    system_adb = shutil.which("adb")
    if system_adb:
        return system_adb
        
    # Standard fallback locations
    common_paths = [
        os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
        "/usr/bin/adb",
        "/usr/local/bin/adb",
        "/opt/homebrew/bin/adb"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    return "adb"

KINDLE_SERIAL = "G0W19E04042401KF"
KINDLE_WIFI_IP = "192.168.0.13:5555"

def resolve_target_device(adb_cmd, config=None):
    """
    Intelligently targets the Kindle Fire HD 8+ (preferring wireless Wi-Fi ADB, falling back to USB).
    Strictly protects and isolates against targeting the user's Pixel phone.
    """
    if config and config.get("adb_target_device"):
        return config["adb_target_device"].strip()
        
    try:
        res = subprocess.run([adb_cmd, "devices"], capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        output = res.stdout.decode("utf-8", errors="ignore")
        
        # 1. Prefer Wireless ADB on local Wi-Fi
        if KINDLE_WIFI_IP in output:
            return KINDLE_WIFI_IP
            
        # 2. Check USB Kindle
        if KINDLE_SERIAL in output:
            return KINDLE_SERIAL
            
        # 3. Attempt auto-reconnect over Wi-Fi if dropped
        subprocess.run([adb_cmd, "connect", KINDLE_WIFI_IP], capture_output=True, timeout=2, creationflags=CREATE_NO_WINDOW)
        return KINDLE_WIFI_IP
    except Exception:
        return KINDLE_WIFI_IP

def enable_wireless_adb(config=None, target_ip="192.168.0.13", port=5555):
    """Switches Kindle Fire into TCP/IP mode and connects wirelessly."""
    adb_cmd = resolve_adb_cmd(config)
    try:
        subprocess.run([adb_cmd, "-s", KINDLE_SERIAL, "tcpip", str(port)], capture_output=True, timeout=4, creationflags=CREATE_NO_WINDOW)
        time.sleep(1)
        res = subprocess.run([adb_cmd, "connect", f"{target_ip}:{port}"], capture_output=True, timeout=4, creationflags=CREATE_NO_WINDOW)
        return f"{target_ip}:{port}" in res.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[myCam Wireless ADB Warning] {e}")
        return False

def get_adb_prefix(config=None):
    adb_cmd = resolve_adb_cmd(config)
    target = resolve_target_device(adb_cmd, config)
    if target:
        return [adb_cmd, "-s", target]
    return [adb_cmd]

def check_adb_connected(config=None):
    prefix = get_adb_prefix(config)
    try:
        res = subprocess.run(
            prefix + ["get-state"],
            capture_output=True, timeout=3,
            creationflags=CREATE_NO_WINDOW
        )
        if res.returncode == 0 and b"device" in res.stdout:
            return True
    except Exception:
        pass
    return False

def focus_ring_app(config=None, package_name="com.ringapp"):
    prefix = get_adb_prefix(config)
    try:
        subprocess.run(
            prefix + ["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, timeout=5, creationflags=CREATE_NO_WINDOW
        )
        time.sleep(1)
        return True
    except Exception:
        return False

def ensure_device_ready(config=None):
    """
    Post-reboot auto-recovery:
    Wakes display, unlocks keyguard, and primes the Ring app in foreground memory.
    Resilient against unattended OEM reboots & updates.
    """
    prefix = get_adb_prefix(config)
    pkg_name = config.get("ring_package_name", "com.ringapp") if config else "com.ringapp"
    try:
        # Keyevent 26: POWER (wake screen)
        subprocess.run(prefix + ["shell", "input", "keyevent", "26"], capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        # Keyevent 82: MENU / UNLOCK (dismiss keyguard lockscreen)
        subprocess.run(prefix + ["shell", "input", "keyevent", "82"], capture_output=True, timeout=3, creationflags=CREATE_NO_WINDOW)
        # Prime Ring app
        subprocess.run(
            prefix + ["shell", "monkey", "-p", pkg_name, "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, timeout=5, creationflags=CREATE_NO_WINDOW
        )
        print("[myCam ADB Recovery] Device primed: screen awake, keyguard cleared, Ring app active.")
        return True
    except Exception as e:
        print(f"[myCam ADB Recovery Error] {e}")
        return False

def record_adb_stream(config, duration_sec=15, title="Ring Doorbell Motion"):
    prefix = get_adb_prefix(config)
    device_label = config.get("adb_target_device", "Android/Kindle Device")
    
    if not check_adb_connected(config):
        print(f"[myCam ADB Silent Poll] {device_label} offline. Falling back to local GDI screen capture for '{title}'...")
        try:
            from recorder import capture_sequence
            return capture_sequence(config, duration_sec=duration_sec, fps=config.get("fps", 10), title=title)
        except Exception as e:
            print(f"[myCam Fallback Error] {e}")
            return None

    pkg_name = config.get("ring_package_name", "com.ringapp")
    storage_dir = config.get("storage_dir", "captures")
    if not os.path.isabs(storage_dir):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        storage_dir = os.path.join(base_dir, storage_dir)
    os.makedirs(storage_dir, exist_ok=True)

    # 1. Bring Ring App to focus on edge device
    focus_ring_app(config, pkg_name)

    # 2. Start Screen Recording on device
    remote_path = "/sdcard/mycam_ring_temp.mp4"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_filename = f"rec_{timestamp}_ring.mp4"
    local_path = os.path.join(storage_dir, local_filename)

    print(f"[myCam ADB] Initiating {duration_sec}s screenrecord on {device_label} for '{title}'...")
    
    try:
        subprocess.run(
            prefix + ["shell", "screenrecord", "--time-limit", str(duration_sec), remote_path],
            capture_output=True, timeout=duration_sec + 5, creationflags=CREATE_NO_WINDOW
        )

        # 3. Pull video file to sovereign storage
        pull_res = subprocess.run(
            prefix + ["pull", remote_path, local_path],
            capture_output=True, timeout=10, creationflags=CREATE_NO_WINDOW
        )

        if pull_res.returncode == 0 and os.path.exists(local_path):
            subprocess.run(prefix + ["shell", "rm", remote_path], capture_output=True, creationflags=CREATE_NO_WINDOW)
            log_event(config, "adb_ring_recording", title, [local_path])
            print(f"[myCam ADB] SUCCESS: Sovereign recording saved -> {local_path}")
            return local_path
        else:
            err_msg = pull_res.stderr.decode("utf-8", errors="replace").strip()
            print(f"[myCam ADB Error] Pull failed: {err_msg}")
    except Exception as e:
        print(f"[myCam ADB Exception] Stream record error: {e}")

    return None
