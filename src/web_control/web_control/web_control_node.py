import socket
import cv2
import threading
import os
import rclpy
import time
from rclpy.node import Node

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from ament_index_python.packages import get_package_share_directory
from flask import Response

from std_msgs.msg import UInt16
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ros_robot_controller_msgs.msg import SetPWMServoState, PWMServoState

import subprocess
from geometry_msgs.msg import Twist

class WebControlNode(Node):

    def __init__(self):
        super().__init__('web_control_node')

        self.current_process = None

        pkg_share = get_package_share_directory('web_control')

        self.app = Flask(
            __name__,
            template_folder=os.path.join(pkg_share, 'templates'),
            static_folder=os.path.join(pkg_share, 'static')
        )

        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        self.app.add_url_rule('/stream', 'stream', self.stream)
        
        self.bridge = CvBridge()
        self.frame = None

        self.camera_ok = False
        self.camera_index = 0
        self.frame = None
        self.frame_lock = threading.Lock()

        # Battery check
        self.battery_voltage = None
        self.create_subscription(
            UInt16,
            '/ros_robot_controller/battery',
            self.battery_callback,
            10
        )
        
        #servo_pub
        self.servo_pub = self.create_publisher(
            SetPWMServoState,
            '/ros_robot_controller/pwm_servo/set_state',
            10
        )

        #Twist_pub
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
            )
        self.rotate_dir = 0

        self.cam_pan = 0
        self.cam_tilt = 0

        self.servo_x = 1500
        self.servo_y = 1500

        # Camera probe (for status only right now)
        self.camera_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.camera_callback,
            10
        )

        self.create_timer(0.05, self.camera_loop)
        self.create_timer(0.05, self.twist_loop)

        # Routes
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/run', 'run', self.run_page)
        self.app.add_url_rule('/api/status', 'api_status', self.api_status)
        self.app.add_url_rule('/api/run_node', 'run_node', self.api_run_node, methods=['POST'])
        self.app.add_url_rule('/api/stop_node', 'stop_node', self.api_stop_node, methods=['POST'])
        self.app.add_url_rule('/api/camera', 'camera_control', self.api_camera_control, methods=['POST'])
        self.app.add_url_rule('/api/rotate', 'rotate', self.api_rotate, methods=['POST'])

        # Start server thread
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()

        self.get_logger().info("UI server started. Open http://<TurboPi-IP>:5000")

    def index(self):
        return render_template('index.html')

    def run_page(self):
        return render_template('run.html')

    def twist_loop(self):

        twist = Twist()

        if self.rotate_dir == 1:
            twist.angular.z = -1.0

        elif self.rotate_dir == -1:
            twist.angular.z = 1.0

        else:
            twist.angular.z = 0.0

        self.cmd_vel_pub.publish(twist)

    def api_status(self):

        ip = self._get_ip_best_effort()

        wifi_ok = (ip not in ("127.0.0.1", "0.0.0.0", "N/A"))
        wifi_txt = "Connected" if wifi_ok else "Disconnected"

        ros_ok = True
        ros_txt = "Active"

        battery_ok = self.battery_voltage is not None
        battery_txt = "N/A"

        cam_ok = self.camera_ok
        cam_txt = "OK" if cam_ok else "Not Detected"

        return jsonify({
            "wifi": wifi_txt,
            "wifi_ok": wifi_ok,
            "ip": ip,
            "ros": ros_txt,
            "ros_ok": ros_ok,
            "battery": f"{self.battery_voltage:.2f} V" if self.battery_voltage else "N/A",
            "battery_ok": battery_ok,
            "camera": f"OK (/dev/video{self.camera_index})" if self.camera_ok else "Not Detected",
            "camera_ok": cam_ok,
        })

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

            if self.current_process is not None:
                self.current_process.kill()
                time.sleep(0.5)

            self.current_process = subprocess.Popen(cmd)

            return jsonify({"message": f"{node} started"})

        except Exception as e:
            return jsonify({"message": str(e)}), 500

    def api_stop_node(self):

        try:

            if self.current_process is not None:
                self.current_process.kill()
                self.current_process = None
                return jsonify({"message": "Node stopped"})
            else:
                return jsonify({"message": "No node running"})

        except Exception as e:
            return jsonify({"message": str(e)}), 500

    def _get_ip_best_effort(self) -> str:

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "N/A"

    def _run_server(self):

        self.socketio.run(
            self.app,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True
        )

    def battery_callback(self, msg):

        self.battery_voltage = msg.data / 1000.0

    def camera_callback(self, msg):

        self.camera_ok = True
        try:
            self.frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            with self.frame_lock:
                self.frame=frame
        except Exception:
            pass

    def camera_loop(self):

        step = 10
        print("camera loop:", self.cam_pan, self.cam_tilt)
        self.servo_x += int(self.cam_pan * step)
        self.servo_y += int(self.cam_tilt * step)

        self.servo_x = max(800, min(2200, self.servo_x))
        self.servo_y = max(800, min(2200, self.servo_y))

        msg = SetPWMServoState()

        s1 = PWMServoState()
        s1.id = [1]
        s1.position = [self.servo_y]

        s2 = PWMServoState()
        s2.id = [2]
        s2.position = [self.servo_x]

        msg.state = [s1, s2]
        msg.duration = 0.05

        self.servo_pub.publish(msg)


    def stream(self):
        return Response(self.generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

    def move_camera(self, pan, tilt):

        self.servo_x += int(pan * 20)
        self.servo_y += int(tilt * 20)

        self.servo_x = max(800, min(2200, self.servo_x))
        self.servo_y = max(800, min(2200, self.servo_y))

        msg = SetPWMServoState()

        s1 = PWMServoState()
        s1.id = [1]
        s1.position = [self.servo_y]

        s2 = PWMServoState()
        s2.id = [2]
        s2.position = [self.servo_x]

        msg.state = [s1, s2]
        msg.duration = 0.1

        self.servo_pub.publish(msg)

    def api_camera_control(self):

        data = request.json

        pan = float(data.get("x", 0))
        tilt = float(data.get("y", 0))
        self.cam_pan = pan
        self.cam_tilt = tilt
        return jsonify({"status": "ok"})

    def generate_frames(self):

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

        while True:

            with self.frame_lock:
                if self.frame is None:
                    frame = None
                else:
                    frame = self.frame.copy()

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


    def api_rotate(self):

        data = request.json
        direction = data.get("direction")

        if direction == "cw":
            self.rotate_dir = 1

        elif direction == "ccw":
            self.rotate_dir = -1

        else:
            self.rotate_dir = 0

        return jsonify({"status": "ok"})

def main(args=None):

    rclpy.init(args=args)

    node = WebControlNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()
