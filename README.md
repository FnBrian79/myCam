# myCam 🛰️
> **Sovereign Edge Camera Sentinel, Autonomous Video Vault & AI Training Feed**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Container: Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Architecture: Local--First](https://img.shields.io/badge/Architecture-Local--First-emerald)](https://github.com/FnBrian79/myCam)

---

## 🏛️ The "Render Unto Caesar" Philosophy

Smart security cameras (Ring, Nest, Blink) often trap your video behind monthly subscriptions, cloud delay, and aggressive notification spam. Meanwhile, millions of cheap Android devices and Amazon Kindle Fire tablets sit forgotten in drawers.

**The Insight:** Amazon owns Ring. Amazon builds Fire OS. 

Instead of fighting the ecosystem, we **"Render unto Caesar that which is Caesar's"**:
1. Take a dedicated, cheap edge device (like a **Kindle Fire HD 8** or any recycled Android phone) plugged 24/7 into your local server over USB.
2. Run Amazon's official Ring app natively on Amazon's own OS.
3. `myCam` silently monitors push alerts via Android Debug Bridge (`adb dumpsys notification`).
4. When motion trips a camera, `myCam` instantly captures high-resolution video streams and snapshots, pulling them directly onto local NVMe storage and indexing them into an immutable local SQLite ledger.

**Zero cloud subscriptions. Zero phone interruptions. 100% sovereign data ownership.**

---

## ⚡ Key Capabilities

* 🛡️ **Zero Phone Interruption**: Dedicated edge hardware means recording never steals focus from your personal smartphone.
* 🔄 **Reboot & OEM Update Resilience**: Amazon or Android pushed an automatic OS update and rebooted? `myCam`'s watchdog detects the reconnect, automatically wakes the display (`KEYEVENT_POWER`), clears the keyguard (`KEYEVENT_MENU`), and primes the Ring app back into foreground RAM.
* 🐳 **Containerized Deployment**: Ready to run via Docker or Docker Compose with ADB, FFmpeg, and Python pre-configured.
* 🤖 **Asynchronous Telegram Training Feed**: Sends captured video clips directly to your private Telegram chat or smartwatch with 1-tap classification buttons (`[ 👤 Person ]`, `[ 🚗 Vehicle ]`, `[ 🐾 Animal ]`, `[ 🍃 False Alarm ]`) to curate ground-truth datasets for local computer vision models.
* 📊 **Dark-Mode Web Dashboard**: Instant HTML5 video playback, event history, and manual trigger controls on port `8765`.
* 🧩 **Modular Spoke Architecture**: Designed as the **Perimeter Vision Spoke** in a sovereign mesh, allowing sister spokes (like an autonomous reconnaissance drone) to subscribe to the event ledger and trigger automated sweeps.

---

## 📐 Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │    Amazon Kindle Fire HD / Android Device    │
                  │  ┌────────────────────────────────────────┐  │
                  │  │  Ring App (Runs 24/7, Receives Push)   │  │
                  │  └────────────────────────────────────────┘  │
                  └───────────────────────┬──────────────────────┘
                                          │ USB / Wireless ADB
                                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        myCam Host Sentinel Daemon                      │
│                                                                        │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  Silent ADB Watchdog    │  │  Event Listener & Webhook API       │  │
│  │  • Dumpsys notification │  │  • http://localhost:8765/dashboard  │  │
│  │  • Reboot auto-recovery │  │  • Dual-write SQLite + JSON ledger  │  │
│  │  • Keyguard & Wake loop │  │  • Local NVMe MP4 / PNG Storage     │  │
│  └────────────┬────────────┘  └──────────────────┬──────────────────┘  │
│               │                                  │                     │
│               ▼                                  ▼                     │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  Telegram Training Feed │  │  Sister Spoke Event Bus (Optional)  │  │
│  │  • Asynchronous clips   │  │  • Drone Aerial Recon Sweep         │  │
│  │  • 1-Tap dataset labels │  │  • Smart Floodlights & Sirens       │  │
│  └─────────────────────────┘  └─────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### Option 1: Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/FnBrian79/myCam.git
   cd myCam
   ```

2. Copy the example config:
   ```bash
   cp config.example.json config.json
   ```

3. Launch the container:
   ```bash
   docker compose up -d
   ```

4. Open the dashboard at `http://localhost:8765/dashboard`.

---

### Option 2: Bare Metal / Local Python

#### Prerequisites
* Python 3.10+
* Android Debug Bridge (`adb`) installed and on your system `PATH`
* An Android device or Amazon Kindle Fire with Developer Options & USB Debugging enabled

#### Installation
```bash
git clone https://github.com/FnBrian79/myCam.git
cd myCam
pip install -r requirements.txt
cp config.example.json config.json
```

#### Configuration (`config.json`)
```json
{
  "storage_dir": "captures",
  "webhook_port": 8765,
  "adb_enabled": true,
  "adb_target_device": "",
  "ring_package_name": "com.ringapp",
  "adb_record_duration": 15,
  "telegram": {
    "enabled": false,
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID",
    "training_mode": true
  }
}
```
*(Leave `adb_target_device` empty to auto-detect the first connected device, or specify your device serial from `adb devices`)*.

#### Run the Sentinel Daemon
```bash
python main.py daemon
```

---

## 🕹️ CLI Commands

```bash
# Start 24/7 background sentinel daemon
python main.py daemon

# Manually trigger a 15-second edge recording
python main.py adb-record --duration 15 --title "Test Trigger"

# Take an immediate full-screen snapshot
python main.py snapshot --title "Manual Check"

# Simulate an incoming motion event
python main.py trigger --title "Front Doorbell Motion" --mode adb

# View recent event history
python main.py list

# Clean up captures older than retention limit
python main.py clean
```

---

## 🤝 Roadmap & Open Issues

This project is open-source and intentionally modular. Dive in, tear it apart, and make it better!

Check out our [GitHub Issues](https://github.com/FnBrian79/myCam/issues) to contribute:
* **Issue #1**: Telegram Training Bot & Interactive Callback Annotation
* **Issue #2**: Sister Spoke Event Bus: Autonomous Recon Drone Interceptor Hook
* **Issue #3**: On-Device Edge Vision Triage (YOLO / MobileNet inference)
* **Issue #4**: Multi-Device ADB Mesh Support (Multiple Kindle / Android edge units)

---

## 📄 License
Released under the [MIT License](LICENSE). Built for sovereign builders and local-first defenders.
