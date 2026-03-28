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
    # SERVO CONTROL
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
    # MOTION HELPERS
    # =========================
    def create_twist(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        return msg

    def rotate_left(self, duration=0.8):
        msg = self.create_twist(0.0, 1.9)
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
    # SCANNING
    # =========================
    def scan_loop(self):

        # fix camera straight
        self.move_servo(1, 1500)
        self.move_servo(2, 1500)

        time.sleep(0.5)

        while self.running and not self.detected:

            if self.distance < 30:
                self.avoid_obstacle()
                continue

            # rotate (scan)
            self.rotate_left(duration=0.8)

            # stop for stable vision
            self.stop_motion()

            time.sleep(0.5)

            if self.detected:
                return

    # =========================
    # YOLO DETECTION
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

            # publish debug frame
            try:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                self.debug_pub.publish(msg)
            except:
                pass

            time.sleep(0.2)

    # =========================
    # OBSTACLE
    # =========================
    def avoid_obstacle(self):

        msg = self.create_twist(0.0, 1.9)
        end_time = time.time() + 0.6

        while time.time() < end_time and self.running and not self.detected:
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.05)

        self.stop_motion()

    # =========================
    # FOUND ACTION
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
