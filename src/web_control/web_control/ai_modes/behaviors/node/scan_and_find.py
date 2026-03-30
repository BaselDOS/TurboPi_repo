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

        while rclpy.ok():

            with self.lock:
                detected = self.target_detected

            # ===== TARGET =====
            if detected:
                self.motion.stop()
                self.alerts.beep5()

                with self.lock:
                    self.target_detected = False

                time.sleep(2)
                continue

            # ===== OBSTACLE =====
            if self.distance < 40:
                self.motion.stop()
                self.motion.rotate_right()
                time.sleep(0.8)
                self.motion.stop()
                continue

            # =========================
            # STEP 1: MOVE FORWARD (REAL MOVE)
            # =========================
            self.motion.forward()
            time.sleep(1.0)   # ← WAS 0.3 → TOO SHORT
            self.motion.stop()

            # =========================
            # STEP 2: SCAN RIGHT (SLOW + STABLE)
            # =========================
            self.head.move(2, 1800, 0.5)

            time.sleep(0.4)  # ← GIVE YOLO TIME

            with self.lock:
                right_boxes = len(self.last_boxes)

            # =========================
            # STEP 3: SCAN LEFT
            # =========================
            self.head.move(2, 1200, 0.5)

            time.sleep(0.4)

            with self.lock:
                left_boxes = len(self.last_boxes)

            # =========================
            # STEP 4: CENTER
            # =========================
            self.head.move(2, 1500, 0.3)

            # =========================
            # STEP 5: DECISION (SMOOTH)
            # =========================
            if right_boxes > left_boxes:
                self.motion.rotate_right()
                time.sleep(0.6)

            elif left_boxes > right_boxes:
                self.motion.rotate_left()
                time.sleep(0.6)

            else:
                # nothing interesting → small search
                self.motion.rotate_left()
                time.sleep(0.4)

            self.motion.stop()


def main():
    rclpy.init()
    node = ScanAndFind()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
