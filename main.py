import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recorder import capture_screenshot, capture_sequence
from recorder_adb import record_adb_stream, check_adb_connected
from listener import run_listener_daemon, start_webhook_server
from storage import load_events, log_event, cleanup_old_media

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # Fallback to example config or defaults
    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.json")
    if os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "storage_dir": "captures",
        "default_capture_mode": "hybrid",
        "record_duration_seconds": 15,
        "fps": 10,
        "target_keywords": ["ring", "motion", "person", "camera", "doorbell", "alert", "detected"],
        "retention_days": 30,
        "webhook_port": 8765,
        "adb_enabled": True,
        "ring_package_name": "com.ringapp",
        "adb_record_duration": 15
    }

def main():
    parser = argparse.ArgumentParser(description="myCam - Sovereign Camera Sentinel & Training Feed")
    subparsers = parser.add_subparsers(dest="command")

    # snapshot command
    parser_snap = subparsers.add_parser("snapshot", help="Take an immediate full-screen snapshot")
    parser_snap.add_argument("--title", default="Manual Snapshot Trigger", help="Event title")

    # record command
    parser_rec = subparsers.add_parser("record", help="Record a high-speed frame sequence")
    parser_rec.add_argument("--duration", type=int, default=10, help="Duration in seconds")
    parser_rec.add_argument("--fps", type=int, default=10, help="Frames per second")
    parser_rec.add_argument("--title", default="Manual Record Trigger", help="Event title")

    # adb-record command
    parser_adb = subparsers.add_parser("adb-record", help="Record native stream from Android/Fire device via ADB")
    parser_adb.add_argument("--duration", type=int, default=15, help="Duration in seconds")
    parser_adb.add_argument("--title", default="Ring Doorbell Alert", help="Event title")

    # trigger command
    parser_trig = subparsers.add_parser("trigger", help="Simulate an incoming notification trigger")
    parser_trig.add_argument("--title", default="Simulated Camera Motion Alert", help="Notification title")
    parser_trig.add_argument("--mode", choices=["snapshot", "hybrid", "adb"], default="hybrid", help="Capture mode")

    # daemon command
    subparsers.add_parser("daemon", help="Run 24/7 notification listener daemon")

    # list command
    subparsers.add_parser("list", help="List recent captured events")

    # clean command
    subparsers.add_parser("clean", help="Clean up media older than retention limit")

    args = parser.parse_args()
    config = load_config()

    if args.command == "snapshot":
        filepath = capture_screenshot(config, title=args.title)
        if filepath:
            log_event(config, "manual_snapshot", args.title, [filepath])
            print(f"SUCCESS: Snapshot created at {filepath}")
        else:
            sys.exit(1)

    elif args.command == "record":
        files = capture_sequence(config, duration_sec=args.duration, fps=args.fps, title=args.title)
        print(f"SUCCESS: Captured {len(files)} frames for event '{args.title}'")

    elif args.command == "adb-record":
        result = record_adb_stream(config, duration_sec=args.duration, title=args.title)
        if result:
            print(f"SUCCESS: ADB Stream recording saved at {result}")
        else:
            print("ADB Stream recording failed or fell back.")

    elif args.command == "trigger":
        print(f"[myCam] Executing simulated trigger: {args.title}")
        if args.mode == "snapshot":
            filepath = capture_screenshot(config, title=args.title)
            if filepath:
                log_event(config, "simulated_snapshot", args.title, [filepath])
        elif args.mode == "adb":
            record_adb_stream(config, duration_sec=15, title=args.title)
        else:
            capture_sequence(config, duration_sec=5, fps=10, title=args.title)

    elif args.command == "daemon":
        run_listener_daemon(config)

    elif args.command == "list":
        events = load_events()
        print(f"=== myCam Sovereign Event History ({len(events)} total events) ===")
        for evt in events[:15]:
            print(f"- [{evt.get('timestamp')}] ID: {evt.get('id')} | Trigger: {evt.get('trigger_type')} | Title: '{evt.get('notification_title')}'")
            print(f"  Media count: {len(evt.get('media', []))} files")

    elif args.command == "clean":
        cleanup_old_media(config)
        print("SUCCESS: Storage retention cleanup complete.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
