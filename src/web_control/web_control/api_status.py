import socket
import time
from flask import jsonify


def register_status_routes(server):
    server.app.add_url_rule('/api/status', 'api_status', lambda: api_status(server))


def api_status(server):
    ip = get_ip()
    wifi_ok = (ip not in ("127.0.0.1", "0.0.0.0", "N/A"))

    now = time.time()

    camera_ok = (now - server.last_camera_time) < 2.5
    battery_ok = (now - server.last_battery_time) < 5.0

    battery = server.battery_voltage if battery_ok else None

    return jsonify({
        "wifi": "Connected" if wifi_ok else "Disconnected",
        "wifi_ok": wifi_ok,
        "ip": ip,

        "ros": "Active",
        "ros_ok": True,

        "battery": f"{battery:.2f} V" if battery is not None else "N/A",
        "battery_ok": battery is not None,

        "camera": "OK" if camera_ok else "Not Detected",
        "camera_ok": camera_ok,

        "mode": server.current_mode
    })


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"
