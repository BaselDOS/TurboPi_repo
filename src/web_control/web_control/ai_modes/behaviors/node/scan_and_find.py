#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import random

from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge

import cv2
import threading
import time

from web_control.ai_modes.behaviors.vision.detector import Detector
from web_control.ai_modes.behaviors.control.motion import Motion
from web_control.ai_modes.behaviors.control.head import Head
from web_control.ai_modes.behaviors.control.alerts import Alerts

from ros_robot_controller_msgs.msg import SetPWMServoState, BuzzerState


class ScanAndFind(Node):

    def __init__(self):
        super().__init__('scan_and_find')

        self.bridge = CvBridge()

        # ===== STATE =====
        self.current_image = None
        self.distance = 100

        self.frame_count = 0
        self.process_every_n = 5

        self.target_detected = False
        self.last_boxes = []

        self.lock = threading.Lock()

        # ===== MODULES =====
        self.detector = Detector()

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.servo_pub = self.create_publisher(SetPWMServoState, 'ros_robot_controller/pwm_servo/set_state', 10)
        self.buzzer_pub = self.create_publisher(BuzzerState, '/ros_robot_controller/set_buzzer', 10)

        self.debug_pub = self.create_publisher(Image, '/avoidance/debug_image', 1)

        self.motion = Motion(self.cmd_pub)
        self.head = Head(self.servo_pub)
        self.alerts = Alerts(self.buzzer_pub)

        # ===== SUBS =====
        self.create_subscription(Image, '/image_raw', self.img_cb, 1)
        self.create_subscription(Int32, 'sonar_controller/get_distance', self.dist_cb, 10)

        # ===== THREADS =====
        threading.Thread(target=self.vision_loop, daemon=True).start()
        threading.Thread(target=self.control_loop, daemon=True).start()

    def img_cb(self, msg):
        try:
            self.current_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except:
            pass

    def dist_cb(self, msg):
        self.distance = msg.data / 10.0

    # =========================
    # VISION THREAD (FAST)
    # =========================
    def vision_loop(self):

        while rclpy.ok():

            if self.current_image is None:
                time.sleep(0.02)
                continue

            frame = self.current_image.copy()

            self.frame_count += 1

            if self.frame_count % self.process_every_n == 0:

                boxes, found = self.detector.detect(frame)

                with self.lock:
                    self.last_boxes = boxes
                    if found:
                        self.target_detected = True

            # ===== DRAW =====
            for (x1, y1, x2, y2, label) in self.last_boxes:

                color = (0, 255, 0)
                if label == "sports ball":
                    color = (0, 0, 255)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )

            # ===== DEBUG STREAM =====
            try:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                self.debug_pub.publish(msg)
            except:
                pass

            time.sleep(0.03)

    # =========================
    # CONTROL THREAD (SLOW)
    # =========================
    def control_loop(self):

        self.last_explore_time = time.time()
        self.explore_interval = 12.0   # between 10–15 sec

        while rclpy.ok():

            now = time.time()

            with self.lock:
                detected = self.target_detected

            # ===== TARGET FOUND =====
            if detected:
                self.motion.stop()
                time.sleep(0.3)
                self.alerts.beep5()

                with self.lock:
                    self.target_detected = False

                time.sleep(2)
                continue

            # =========================
            # REAL-TIME OBSTACLE AVOIDANCE
            # =========================
            if self.distance < 35:
                self.motion.stop()

                # step back
                self.motion._send(-0.2, 0.0)
                time.sleep(0.4)
                self.motion.stop()

                # turn random direction (NO bias)
                if random.random() > 0.5:
                    self.motion.rotate_left()
                else:
                    self.motion.rotate_right()

                time.sleep(0.5)
                self.motion.stop()

                continue

            # =========================
            # PERIODIC EXPLORATION (10–15 sec)
            # =========================
            if now - self.last_explore_time > self.explore_interval:

                self.motion.stop()
                time.sleep(0.4)

                # ===== SMALL RANDOM ROTATION (~45°) =====
                if random.random() > 0.5:
                    self.motion.rotate_left()
                else:
                    self.motion.rotate_right()

                time.sleep(0.4)
                self.motion.stop()
                time.sleep(0.3)

                right_score = 0
                left_score = 0

                # ===== SCAN RIGHT (~1 sec) =====
                self.head.move(2, 1800, 0.8)
                for _ in range(6):
                    time.sleep(0.15)
                    with self.lock:
                        right_score += len(self.last_boxes)

                # ===== SCAN LEFT (~1 sec) =====
                self.head.move(2, 1200, 0.8)
                for _ in range(6):
                    time.sleep(0.15)
                    with self.lock:
                        left_score += len(self.last_boxes)

                # ===== CENTER =====
                self.head.move(2, 1500, 0.6)
                time.sleep(0.3)

                # ===== DECISION =====
                if right_score > left_score + 2:
                    self.motion.rotate_right()
                    time.sleep(0.4)

                elif left_score > right_score + 2:
                    self.motion.rotate_left()
                    time.sleep(0.4)

                # else → keep direction (no forced turn)

                self.motion.stop()

                # reset timer
                self.last_explore_time = now

                continue

            # =========================
            # NORMAL CONTINUOUS DRIVE
            # =========================
            self.motion.forward()
            time.sleep(0.1)


def main():
    rclpy.init()
    node = ScanAndFind()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
