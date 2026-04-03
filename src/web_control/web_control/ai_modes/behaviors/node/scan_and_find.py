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
from web_control.ai_modes.behaviors.control.control_loop import ControlLoop

from ros_robot_controller_msgs.msg import SetPWMServoState, BuzzerState


class ScanAndFind(Node):

    def __init__(self):
        super().__init__('scan_and_find')

        self.bridge = CvBridge()

        # ===== STATE =====
        self.current_image = None
        self.distance = 100

        self.frame_count = 0
        self.process_every_n = 3

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
        self.control = ControlLoop(
            motion=self.motion,
            alerts=self.alerts,
            head=self.head,
            get_frame=lambda: self.current_image,
            get_distance=lambda: self.distance,
            get_boxes=lambda: self.last_boxes,
            lock=self.lock
        )

        # ===== SUBS =====
        self.create_subscription(Image, '/image_raw', self.img_cb, 1)
        self.create_subscription(Int32, 'sonar_controller/get_distance', self.dist_cb, 10)

        # ===== THREADS =====
        threading.Thread(target=self.vision_loop, daemon=True).start()
        threading.Thread(target=self.control.run, daemon=True).start()

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

            frame = self.current_image

            self.frame_count += 1

            if self.frame_count % self.process_every_n == 0:

                boxes, found = self.detector.detect(frame)

                with self.lock:
                    self.last_boxes = boxes
                if found:
                    self.control.update_target(True)
                else:
                    self.control.update_target(False) 
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

def main():
    rclpy.init()
    node = ScanAndFind()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

