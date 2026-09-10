"""
alexa_bridge.py - Sovereign Alexa Local UPnP/WeMo Infiltration Bridge
====================================================================
Acts like a 'Ghost in the Shell' on your home network:
  - Emulates a standard local Belkin WeMo smart switch over UPnP / SSDP (port 1900).
  - Requires ZERO Amazon developer accounts, ZERO custom Alexa skills, and ZERO cloud APIs.
  - Amazon Echo devices auto-discover it on local Wi-Fi: 'myCam Sentinel Alert'.
  - When myCam's local vision models detect an unrecognized visitor, this bridge
    pulses the virtual switch ON for 2 seconds.
  - An ordinary Alexa Routine catches the switch:
      [When 'myCam Sentinel Alert' turns ON] ➔ [Alexa announces alert on all Echo speakers].
"""

import socket
import struct
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

DEVICE_NAME = "myCam Sentinel Alert"
SETUP_PORT = 52000

WEMO_SETUP_XML = f"""<?xml version="1.0"?>
<root xmlns="urn:Belkin:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:Belkin:device:controllee:1</deviceType>
    <friendlyName>{DEVICE_NAME}</friendlyName>
    <manufacturer>Sovereign Mesh</manufacturer>
    <modelName>myCam Virtual Sentinel</modelName>
    <modelNumber>1.0</modelNumber>
    <serialNumber>SOV-MYCAM-001</serialNumber>
    <UDN>uuid:Socket-1_0-221438MYCAM01</UDN>
    <binaryState>0</binaryState>
    <serviceList>
      <service>
        <serviceType>urn:Belkin:service:basicevent:1</serviceType>
        <serviceId>urn:Belkin:serviceId:basicevent1</serviceId>
        <controlURL>/upnp/control/basicevent1</controlURL>
        <eventSubURL>/upnp/event/basicevent1</eventSubURL>
        <SCPDURL>/eventservice.xml</SCPDURL>
      </service>
    </serviceList>
  </device>
</root>"""

EVENT_SERVICE_XML = """<?xml version="1.0"?>
<scpd xmlns="urn:Belkin:service-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <actionList>
    <action>
      <name>SetBinaryState</name>
      <argumentList>
        <argument>
          <name>BinaryState</name>
          <direction>in</direction>
          <relatedStateVariable>BinaryState</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>GetBinaryState</name>
      <argumentList>
        <argument>
          <name>BinaryState</name>
          <direction>out</direction>
          <relatedStateVariable>BinaryState</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
  </actionList>
</scpd>"""

CURRENT_STATE = "0"
SUBSCRIBERS = set()

def get_local_ip():
    """Finds primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.1.1', 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class WeMoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet background operation

    def do_GET(self):
        if self.path == "/setup.xml":
            self.send_response(200)
            self.send_header("Content-Type", "text/xml")
            self.end_headers()
            self.wfile.write(WEMO_SETUP_XML.encode("utf-8"))
        elif self.path == "/eventservice.xml":
            self.send_response(200)
            self.send_header("Content-Type", "text/xml")
            self.end_headers()
            self.wfile.write(EVENT_SERVICE_XML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global CURRENT_STATE
        if "/upnp/control/basicevent1" in self.path:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
            
            if "SetBinaryState" in body:
                if "<BinaryState>1</BinaryState>" in body:
                    CURRENT_STATE = "1"
                else:
                    CURRENT_STATE = "0"
            
            response_xml = f"""<?xml version="1.0"?>
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
              <s:Body>
                <u:GetBinaryStateResponse xmlns:u="urn:Belkin:service:basicevent:1">
                  <BinaryState>{CURRENT_STATE}</BinaryState>
                </u:GetBinaryStateResponse>
              </s:Body>
            </s:Envelope>"""
            
            self.send_response(200)
            self.send_header("Content-Type", 'text/xml; charset="utf-8"')
            self.end_headers()
            self.wfile.write(response_xml.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server(local_ip):
    server = HTTPServer((local_ip, SETUP_PORT), WeMoHandler)
    server.serve_forever()

def run_ssdp_listener(local_ip):
    """Responds to Alexa Echo SSDP M-SEARCH discovery broadcasts."""
    ssdp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    ssdp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to standard SSDP port
    try:
        ssdp_sock.bind(('', 1900))
        mreq = struct.pack("4sl", socket.inet_aton("239.255.255.250"), socket.INADDR_ANY)
        ssdp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        print(f"[Alexa Bridge] SSDP socket bind notice: {e}")
        return

    location_url = f"http://{local_ip}:{SETUP_PORT}/setup.xml"
    
    ssdp_response = (
        "HTTP/1.1 200 OK\r\n"
        "CACHE-CONTROL: max-age=86400\r\n"
        "DATE: Mon, 07 Sep 2026 18:00:00 GMT\r\n"
        "EXT:\r\n"
        f"LOCATION: {location_url}\r\n"
        "OPT: \"http://schemas.upnp.org/upnp/1/0/\"; ns=01\r\n"
        "01-NLS: b9200eb-13dd-1118-9fc0-000000000000\r\n"
        "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
        "ST: urn:Belkin:device:controllee:1\r\n"
        "USN: uuid:Socket-1_0-221438MYCAM01::urn:Belkin:device:controllee:1\r\n\r\n"
    ).encode("utf-8")

    while True:
        try:
            data, addr = ssdp_sock.recvfrom(2048)
            msg = data.decode("utf-8", errors="ignore")
            if "M-SEARCH" in msg and ("urn:Belkin:device:controllee:1" in msg or "ssdp:all" in msg or "upnp:rootdevice" in msg):
                ssdp_sock.sendto(ssdp_response, addr)
        except Exception:
            pass

def start_alexa_bridge():
    """Starts the background Alexa discovery and control thread."""
    local_ip = get_local_ip()
    t_http = threading.Thread(target=run_http_server, args=(local_ip,), daemon=True)
    t_ssdp = threading.Thread(target=run_ssdp_listener, args=(local_ip,), daemon=True)
    t_http.start()
    t_ssdp.start()
    print(f"[Alexa Bridge] Ghost-in-the-Shell online at {local_ip}:{SETUP_PORT} ('{DEVICE_NAME}')")

def trigger_alexa_alert(reason="Unknown Visitor Detected"):
    """Pulses the virtual WeMo switch ON for 2 seconds to fire Alexa routines."""
    global CURRENT_STATE
    print(f"[Alexa Bridge] 🚨 Triggering House-Wide Voice Announcement: '{reason}'")
    CURRENT_STATE = "1"
    
    def reset_state():
        time.sleep(2)
        global CURRENT_STATE
        CURRENT_STATE = "0"
        
    threading.Thread(target=reset_state, daemon=True).start()

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("==========================================================")
    print(f" 🔊 Alexa Local Infiltration Bridge ('Ghost in the Shell')")
    print("==========================================================")
    print(f"Host LAN IP:  {local_ip}")
    print(f"Device Name:  '{DEVICE_NAME}'")
    print(f"Discovery:    Ask Alexa: 'Alexa, discover devices'")
    print("==========================================================\n")
    start_alexa_bridge()
    
    print("[*] Press Enter to simulate an Intruder Alert pulse...")
    try:
        while True:
            input()
            trigger_alexa_alert("Simulated Intruder Trigger")
    except KeyboardInterrupt:
        pass
