import pytest
import alexa_bridge
from alexa_bridge import (
    WEMO_SETUP_XML,
    EVENT_SERVICE_XML,
    DEVICE_NAME,
    get_local_ip,
    trigger_alexa_alert
)

def test_wemo_xml_templates():
    assert DEVICE_NAME in WEMO_SETUP_XML
    assert "urn:Belkin:device:controllee:1" in WEMO_SETUP_XML
    assert "SetBinaryState" in EVENT_SERVICE_XML
    assert "GetBinaryState" in EVENT_SERVICE_XML

def test_get_local_ip():
    ip = get_local_ip()
    assert isinstance(ip, str)
    assert len(ip.split('.')) == 4

def test_trigger_alexa_alert():
    trigger_alexa_alert("Unit Test Voice Announcement")
    assert alexa_bridge.CURRENT_STATE == "1"
