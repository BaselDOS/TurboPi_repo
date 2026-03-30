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
from web_control.ai_modes.behaviors.vision.free_space import FreeSpace
from web_control.ai_modes.behaviors.vision.stuck_detector import StuckDetector

from web_control.ai_modes.behaviors.control.motion import Motion
from web_control.ai_modes.behaviors.control.head import Head
from web_control.ai_modes.behaviors.control.alerts import Alerts

from ros_robot_controller_msgs.msg import SetPWMServoState, BuzzerState


class ScanAndFind(Node):

    def __init__(self):
        super().__init__('scan_and_find')

        self.bridge = CvBridge()

        self.current_image = None
        self.distance = 100

        self.detector = Detector()
        self.space = FreeSpace()
        self.stuck = StuckDetector()

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.servo_pub = self.create_publisher(SetPWMServoState, 'ros_robot_controller/pwm_servo/set_state', 10)
        self.buzzer_pub = self.create_publisher(BuzzerState, '/ros_robot_controller/set_buzzer', 10)

        self.motion = Motion(self.cmd_pub)
        self.head = Head(self.servo_pub)
        self.alerts = Alerts(self.buzzer_pub)

        self.create_subscription(Image, '/image_raw', self.img_cb, 1)
        self.create_subscription(Int32, 'sonar_controller/get_distance', self.dist_cb, 10)

        threading.Thread(target=self.loop, daemon=True).start()

    def img_cb(self, msg):
        self.current_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")

    def dist_cb(self, msg):
        self.distance = msg.data / 10.0

    def loop(self):

        while rclpy.ok():

            if self.current_image is None:
                time.sleep(0.05)
                continue

            frame = self.current_image

            boxes, found = self.detector.detect(frame)

            if found:
                self.motion.stop()
                self.alerts.beep5()
                return

            if self.distance < 40:
                self.motion.stop()
                self.motion.rotate_right(1.5)
                continue

            if self.stuck.is_stuck(frame):
                self.motion.stop()
                self.motion.rotate_left(2.0)
                continue

            # ===== MOVE =====
            self.motion.forward(1.5)
            self.motion.stop()

            # ===== SCAN =====
            self.head.move(2, 1800, 1.0)
            right_score = self.space.analyze(frame)["right"]

            self.head.move(2, 1200, 1.0)
            left_score = self.space.analyze(frame)["left"]

            self.head.move(2, 1500, 0.5)

            # ===== DECIDE =====
            if right_score < left_score:
                self.motion.rotate_right(1.0)
            else:
                self.motion.rotate_left(1.0)

    # (optional: reuse your debug stream code if needed)


def main():
    rclpy.init()
    node = ScanAndFind()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
