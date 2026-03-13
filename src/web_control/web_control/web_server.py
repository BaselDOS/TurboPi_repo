import socket
import cv2
import threading
import time
import subprocess

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO
from cv_bridge import CvBridge

from std_msgs.msg import UInt16
from sensor_msgs.msg import Image


class WebServer:

    def __init__(self, node, pkg_share):

        self.node = node
        self.robot = node.robot

        self.bridge = CvBridge()

        self.frame = None
        self.frame_lock = threading.Lock()

        self.camera_ok = False
        self.camera_index = 0

        self.battery_voltage = None

        self.app = Flask(
            __name__,
            template_folder=pkg_share + '/templates',
            static_folder=pkg_share + '/static'
        )

        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # ROS subscriptions
        node.create_subscription(
            UInt16,
            '/ros_robot_controller/battery',
            self.battery_callback,
            10
        )

        node.create_subscription(
            Image,
            '/image_raw',
            self.camera_callback,
            10
        )

        # Routes
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/run', 'run', self.run_page)

        self.app.add_url_rule('/api/status', 'api_status', self.api_status)
        
        self.app.add_url_rule('/api/run_node', 'run_node', self.api_run_node, methods=['POST'])
        self.app.add_url_rule('/api/stop_node', 'stop_node', self.api_stop_node, methods=['POST'])

        self.app.add_url_rule('/api/move', 'move', self.api_move, methods=['POST'])
        self.app.add_url_rule('/api/rotate', 'rotate', self.api_rotate, methods=['POST'])
        self.app.add_url_rule('/api/camera', 'camera', self.api_camera, methods=['POST'])

        self.app.add_url_rule('/stream', 'stream', self.stream)

        # Start server
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()

    def index(self):
        return render_template('index.html')

    def run_page(self):
        return render_template('run.html')

    def api_move(self):

        data = request.json

        self.robot.move_x = float(data.get("x", 0))
        self.robot.move_y = float(data.get("y", 0))

        return jsonify({"status": "ok"})

    def api_rotate(self):

        data = request.json
        direction = data.get("direction")

        if direction == "cw":
            self.robot.rotate_dir = 1

        elif direction == "ccw":
            self.robot.rotate_dir = -1

        else:
            self.robot.rotate_dir = 0

        return jsonify({"status": "ok"})

    def api_camera(self):

        data = request.json

        self.robot.cam_pan = float(data.get("x", 0))
        self.robot.cam_tilt = float(data.get("y", 0))

        return jsonify({"status": "ok"})

    def api_status(self):

        ip = self._get_ip_best_effort()

        wifi_ok = (ip not in ("127.0.0.1", "0.0.0.0", "N/A"))

        return jsonify({

            "wifi": "Connected" if wifi_ok else "Disconnected",
            "wifi_ok": wifi_ok,
            "ip": ip,

            "ros": "Active",
            "ros_ok": True,

            "battery": f"{self.battery_voltage:.2f} V" if self.battery_voltage else "N/A",
            "battery_ok": self.battery_voltage is not None,

            "camera": "OK" if self.camera_ok else "Not Detected",
            "camera_ok": self.camera_ok
        })

    def _get_ip_best_effort(self):

        try:

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s.connect(("8.8.8.8", 80))

            ip = s.getsockname()[0]

            s.close()

            return ip

        except Exception:

            return "N/A"

    def battery_callback(self, msg):

        self.battery_voltage = msg.data / 1000.0

    def camera_callback(self, msg):

        self.camera_ok = True

        try:

            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

            with self.frame_lock:

                self.frame = frame

        except Exception:
            pass

    def stream(self):

        return Response(
            self.generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    def generate_frames(self):

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

        while True:

            with self.frame_lock:

                frame = None if self.frame is None else self.frame.copy()

            if frame is None:

                time.sleep(0.01)

                continue

            frame = cv2.resize(frame, (640, 480))

            ret, buffer = cv2.imencode('.jpg', frame, encode_param)

            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   frame_bytes +
                   b'\r\n')

            time.sleep(0.03)
    
    def api_run_node(self):

        data = request.json
        node = data.get("node")

        if node == "body_control":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/body_control.py"]

        elif node == "pose":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pose.py"]

        elif node == "joystick":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pos.py"]

        else:
            return jsonify({"message": "Unknown node"}), 400

        try:

            if hasattr(self, "current_process") and self.current_process:
                self.current_process.kill()
                time.sleep(0.5)

            self.current_process = subprocess.Popen(cmd)

            return jsonify({"message": f"{node} started"})

        except Exception as e:

            return jsonify({"message": str(e)}), 500

    
    def api_stop_node(self):

        try:

            if hasattr(self, "current_process") and self.current_process:

                self.current_process.kill()
                self.current_process = None

                return jsonify({"message": "Node stopped"})

            else:

                return jsonify({"message": "No node running"})

        except Exception as e:

            return jsonify({"message": str(e)}), 500

    def _run_server(self):

        self.socketio.run(
            self.app,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True
        )
