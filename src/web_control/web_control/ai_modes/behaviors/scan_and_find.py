#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import threading
import time

from ultralytics import YOLO

from ros_robot_controller_msgs.msg import BuzzerState, SetPWMServoState, PWMServoState


class ScanFindNode(Node):

    def __init__(self):
        super().__init__('scan_find_node')

        self.bridge = CvBridge()

        # ===== STATE =====
        self.current_image = None
        self.detected = False
        self.running = True
        self.distance = 100

        # ===== CONTROL =====
        self.last_scan_time = time.time()
        self.last_escape_time = time.time()
        self.turn_left_next = True

        # ===== YOLO =====
        self.model = YOLO("yolov8n.pt")
        self.target_class = "sports ball"

        # ===== SUBSCRIBERS =====
        self.create_subscription(Image, 'image_raw', self.image_callback, 1)
        self.create_subscription(Int32, 'sonar_controller/get_distance', self.distance_callback, 10)

        # ===== PUBLISHERS =====
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.buzzer_pub = self.create_publisher(BuzzerState, '/ros_robot_controller/set_buzzer', 10)
        self.servo_pub = self.create_publisher(SetPWMServoState, 'ros_robot_controller/pwm_servo/set_state', 10)
        self.debug_pub = self.create_publisher(Image, '/avoidance/debug_image', 1)

        # ===== THREADS =====
        threading.Thread(target=self.scan_loop, daemon=True).start()
        threading.Thread(target=self.detection_loop, daemon=True).start()

    # =========================
    # CAMERA
    # =========================
    def image_callback(self, msg):
        self.current_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")

    # =========================
    # SONAR
    # =========================
    def distance_callback(self, msg):
        self.distance = msg.data / 10.0

    # =========================
    # SERVO
    # =========================
    def move_servo(self, servo_id, position):
        msg = SetPWMServoState()
        msg.duration = 0.2

        pos = PWMServoState()
        pos.id = [servo_id]
        pos.position = [int(position)]

        msg.state = [pos]
        self.servo_pub.publish(msg)

    # =========================
    # MOTION
    # =========================
    def create_twist(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        return msg

    def move_forward(self, duration=2.0):

        boost = self.create_twist(0.5, 0.0)
        for _ in range(5):
            self.cmd_vel_pub.publish(boost)
            time.sleep(0.05)

        msg = self.create_twist(0.4, 0.0)
        end_time = time.time() + duration

        while time.time() < end_time and self.running and not self.detected:
            if self.distance < 45:
                self.stop_motion()
                return
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.05)

    def rotate_left(self, duration=1.5):
        msg = self.create_twist(0.08, 1.6)
        end_time = time.time() + duration

        while time.time() < end_time and self.running and not self.detected:
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.05)

    def rotate_right(self, duration=1.5):
        msg = self.create_twist(0.08, -1.6)
        end_time = time.time() + duration

        while time.time() < end_time and self.running and not self.detected:
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.05)

    def stop_motion(self):
        msg = self.create_twist(0.0, 0.0)
        for _ in range(5):
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.05)

    # =========================
    # CAMERA SCAN
    # =========================
    def perform_camera_scan(self):

        self.get_logger().info("Camera scan")

        self.stop_motion()

        # RIGHT (wide + slow)
        self.move_servo(2, 1850)
        time.sleep(1.5)

        if self.detected:
            return

        # LEFT
        self.move_servo(2, 1150)
        time.sleep(1.5)

        if self.detected:
            return

        # CENTER
        self.move_servo(2, 1500)
        time.sleep(0.5)

    # =========================
    # MAIN LOOP
    # =========================
    def scan_loop(self):

        self.move_servo(1, 1500)
        self.move_servo(2, 1500)

        time.sleep(0.5)

        while self.running and not self.detected:

            now = time.time()

            # ===== FORCED ESCAPE =====
            if now - self.last_escape_time > 12.0:
                self.get_logger().info("ESCAPE MODE")
                self.stop_motion()
                self.rotate_right(duration=2.5)
                self.last_escape_time = now
                continue

            # ===== CAMERA SCAN =====
            if now - self.last_scan_time > 5.0:
                self.perform_camera_scan()
                self.last_scan_time = now
                continue

            # ===== OBSTACLE =====
            if self.distance < 45:
                self.avoid_obstacle()
                continue

            # ===== MOVE =====
            self.move_forward(duration=2.0)

            if self.detected:
                return

            # ===== ALTERNATING ROTATION =====
            if self.turn_left_next:
                self.rotate_left(duration=1.5)
            else:
                self.rotate_right(duration=1.5)

            self.turn_left_next = not self.turn_left_next

    # =========================
    # DETECTION
    # =========================
    def detection_loop(self):

        while self.running:

            if self.current_image is None:
                time.sleep(0.1)
                continue

            frame = self.current_image.copy()

            results = self.model(frame, verbose=False)

            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    label = self.model.names[cls]

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                    cv2.putText(frame, label, (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

                    if label == self.target_class:
                        self.get_logger().info(f"FOUND: {label}")
                        self.detected = True
                        self.on_found()

            # CAMERA OBSTACLE
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5,5), 0)
            edges = cv2.Canny(blur, 50, 150)

            h, w = edges.shape
            center = edges[:, w//3:2*w//3]

            if cv2.countNonZero(center) > 6000 and not self.detected:
                self.get_logger().info("Camera obstacle")
                self.avoid_obstacle()

            try:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                self.debug_pub.publish(msg)
            except:
                pass

            time.sleep(0.3)

    # =========================
    # AVOIDANCE
    # =========================
    def avoid_obstacle(self):

        self.get_logger().info("Obstacle detected")

        self.stop_motion()

        back = self.create_twist(-0.3, 0.0)
        for _ in range(12):
            self.cmd_vel_pub.publish(back)
            time.sleep(0.05)

        rot = self.create_twist(0.0, 1.5)
        for _ in range(15):
            self.cmd_vel_pub.publish(rot)
            time.sleep(0.05)

        self.stop_motion()

    # =========================
    # FOUND
    # =========================
    def on_found(self):
        self.stop_motion()
        self.beep_5_times()

    def beep_5_times(self):
        for _ in range(5):
            msg = BuzzerState()
            msg.freq = 2000
            msg.on_time = 0.2
            msg.off_time = 0.1
            msg.repeat = 1
            self.buzzer_pub.publish(msg)
            time.sleep(0.4)


def main():
    rclpy.init()
    node = ScanFindNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
