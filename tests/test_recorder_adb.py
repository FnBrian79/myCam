import os
import pytest
from recorder_adb import (
    resolve_adb_cmd,
    get_adb_prefix,
    check_adb_connected,
    ensure_device_ready,
    record_adb_stream
)

def test_resolve_adb_cmd():
    config = {"adb_binary_path": "/fake/nonexistent/adb"}
    # Non-existent config path should fall back
    cmd = resolve_adb_cmd(config)
    assert isinstance(cmd, str)

def test_get_adb_prefix():
    config = {"adb_target_device": "192.168.1.100:5555"}
    prefix = get_adb_prefix(config)
    assert "-s" in prefix
    assert "192.168.1.100:5555" in prefix

def test_check_adb_connected():
    # Will safely return False or True depending on ADB state without throwing unhandled exceptions
    is_conn = check_adb_connected({})
    assert isinstance(is_conn, bool)

def test_record_adb_stream_fallback(tmp_path):
    # When ADB is disconnected, record_adb_stream falls back to capture_sequence
    config = {
        "storage_dir": str(tmp_path),
        "adb_target_device": "offline_device_xyz",
        "fps": 2
    }
    result = record_adb_stream(config, duration_sec=1, title="ADB Fallback Test")
    # Result is either list of files from capture_sequence or single MP4 if connected
    assert result is not None
