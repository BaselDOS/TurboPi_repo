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
from web_control.ai_modes.behaviors.control.control_loop import ControlLoop

from ros_robot_controller_msgs.msg import SetPWMServoState, BuzzerState


class ScanAndFind(Node):

    def __init__(self):
        super().__init__('scan_and_find')

        self.bridge = CvBridge()

        # ===== STATE =====
        self.current_image = None
        self.distance = 100
        self.last_boxes = []

        self.lock = threading.Lock()

        # ===== DETECTION TIMING =====
        self.detect_interval = 0.10   # run YOLO about 10 times/sec
        self.last_detect_time = 0.0

        # ===== MODULES =====
        self.detector = Detector()

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.servo_pub = self.create_publisher(
            SetPWMServoState,
            'ros_robot_controller/pwm_servo/set_state',
            10
        )
        self.buzzer_pub = self.create_publisher(
            BuzzerState,
            '/ros_robot_controller/set_buzzer',
            10
        )

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
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.current_image = frame
        except Exception:
            pass

    def dist_cb(self, msg):
        self.distance = msg.data / 10.0

    # =========================
    # VISION THREAD
    # =========================
    def vision_loop(self):

        while rclpy.ok():

            if self.current_image is None:
                time.sleep(0.01)
                continue

            # always work on the latest frame only
            frame = self.current_image.copy()
            now = time.time()

            # run YOLO on time basis, not every N frames
            if now - self.last_detect_time >= self.detect_interval:
                boxes, found = self.detector.detect(frame)

                with self.lock:
                    self.last_boxes = boxes

                self.control.update_target(found)
                self.last_detect_time = now
            else:
                with self.lock:
                    boxes = list(self.last_boxes)

            # ===== DRAW =====
            for (x1, y1, x2, y2, label) in boxes:

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
            except Exception:
                pass

            time.sleep(0.01)


def main():
    rclpy.init()
    node = ScanAndFind()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
