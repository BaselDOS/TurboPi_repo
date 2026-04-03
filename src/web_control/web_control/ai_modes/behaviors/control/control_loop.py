import time
import cv2

from web_control.ai_modes.behaviors.vision.vision_detector import VisionDetector
from web_control.ai_modes.behaviors.vision.optical_flow import OpticalFlowDetector
from web_control.ai_modes.behaviors.control.motion_controller import MotionController
from web_control.ai_modes.behaviors.control.target_follow import TargetFollow


class ControlLoop:

    def __init__(self, motion, alerts, head, get_frame, get_distance, get_boxes, lock):

        self.motion = motion
        self.alerts = alerts
        self.head = head

        self.get_frame = get_frame
        self.get_distance = get_distance
        self.get_boxes = get_boxes

        self.lock = lock

        # ===== CORE =====
        self.vision = VisionDetector()
        self.flow = OpticalFlowDetector()
        self.controller = MotionController()
        
        self.target_follow = TargetFollow()

        # ===== STATE MACHINE =====
        self.state = "SEARCH"
        self.last_target_time = 0

        # ===== HEAD MEMORY =====
        self.last_servo = 1500

        # scan behavior
        self.last_scan = 0
        self.scan_interval = 5.0

    # =========================
    def update_target(self, detected):
        with self.lock:
            if detected:
                self.last_target_time = time.time()
                self.state = "FOLLOW"

    # =========================
    def run(self):

        while True:

            frame = self.get_frame()
            if frame is None:
                time.sleep(0.02)
                continue

            distance = self.get_distance()
            boxes = self.get_boxes()

            now = time.time()

            # =========================
            # STATE TRANSITION
            # =========================
            if self.state == "FOLLOW" and (now - self.last_target_time > 3.0):
                self.state = "SEARCH"

            # =========================
            # 🎯 FOLLOW MODE
            # =========================
            if self.state == "FOLLOW":

                cmd = self.target_follow.compute(frame, boxes)

                if cmd is not None:
                    servo_pos, lin_x, ang_z = cmd

                    self.last_servo = servo_pos

                    # smooth head
                    self.head.move(2, int(servo_pos), 0.02)

                    # gentle follow motion
                    self.motion._send(float(lin_x), float(ang_z))

                else:
                    self.head.move(2, int(self.last_servo), 0.02)
                    self.motion.stop()

                time.sleep(0.01)
                continue

            # =========================
            # 🔍 SEARCH MODE
            # =========================
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow_val = self.flow.compute(gray)

            left, center, right = self.vision.detect(frame)

            lin_x, lin_y, ang_z = self.controller.decide(
                left,
                center,
                right,
                flow_val,
                distance
            )

            self.motion._send(float(lin_x), float(ang_z))

            # =========================
            # 🔍 SCAN (ONLY IN SEARCH)
            # =========================
            if self.state == "SEARCH" and time.time() - self.last_scan > self.scan_interval: 

                self.motion.stop()
                time.sleep(0.3)

                # center
                self.head.move(2, 1500, 0.3)
                time.sleep(1.0)

                # right
                self.head.move(2, 1800, 0.3)
                time.sleep(0.5)

                # left
                self.head.move(2, 1200, 0.3)
                time.sleep(0.5)

                # back to center
                self.head.move(2, 1500, 0.3)

                self.last_scan = time.time()

            time.sleep(0.01)
