import time
import cv2
import random

from web_control.ai_modes.behaviors.vision.free_space import FreeSpace
from web_control.ai_modes.behaviors.vision.stuck_detector import StuckDetector


class ControlLoop:

    def __init__(self, motion, alerts, head, get_frame, get_distance, get_boxes, lock):

        self.motion = motion
        self.alerts = alerts
        self.head = head

        self.get_frame = get_frame
        self.get_distance = get_distance
        self.get_boxes = get_boxes

        self.lock = lock

        self.free_space = FreeSpace()
        self.stuck_detector = StuckDetector()

        self.state = "SEARCH"
        self.state_start = time.time()

        self.target_detected = False

        self.last_escape_time = 0
        self.escape_cooldown = 3.0

        self.last_forward_time = 0

        self.last_turn = None   # 🔥 NEW

        # ===== SCAN SYSTEM =====
        self.last_scan_time = 0
        self.scan_interval = 6.0

        # ===== STARTUP CALM =====
        self.start_time = time.time()

    def update_target(self, detected):
        with self.lock:
            self.target_detected = detected

    def run(self):

        while True:

            frame = self.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            # ===== OBJECT SIZE =====
            boxes = self.get_boxes()
            object_close = False

            for (x1, y1, x2, y2, label) in boxes:
                area = (x2 - x1) * (y2 - y1)
                if area > 45000:
                    object_close = True
                    break

            distance = self.get_distance()

            with self.lock:
                detected = self.target_detected

            # ===== TARGET =====
            if detected:
                self.motion.stop()
                time.sleep(0.3)
                self.alerts.beep5()

                with self.lock:
                    self.target_detected = False

                self.state = "SEARCH"
                continue

            # ===== SCAN TRIGGER =====
            if time.time() - self.last_scan_time > self.scan_interval and self.state == "SEARCH":
                self.state = "SCAN"

            # ===== STARTUP PROTECTION =====
            startup = (time.time() - self.start_time) < 2.0

            # ===== HARD ESCAPE (VERY CLOSE) 🔥
            if not startup and distance < 20:
                self.state = "ESCAPE"

            # ===== STUCK =====
            forwarding = (time.time() - self.last_forward_time) < 0.5
            is_stuck = self.stuck_detector.is_stuck(frame)

            if forwarding and is_stuck and (time.time() - self.last_escape_time > self.escape_cooldown):
                self.state = "ESCAPE"

            # ===== OBSTACLE =====
            if not startup and (
                distance < 35 or
                object_close
            ) and self.state not in ["ESCAPE"]:
                self.state = "AVOID"

            # ===== STATES =====

            if self.state == "SEARCH":

                self.motion.forward()
                self.last_forward_time = time.time()
                time.sleep(0.3)

            elif self.state == "AVOID":

                self.motion.stop()
                time.sleep(0.1)

                # 🔥 IF TOO CLOSE → BACK FIRST
                if distance < 25:
                    self.motion.backward()
                    time.sleep(0.4)
                    self.motion.stop()

                spaces = self.free_space.analyze(frame)

                # 🔥 PREVENT LEFT-RIGHT LOOP
                if abs(spaces["left"] - spaces["right"]) < 1000:

                    if self.last_turn == "left":
                        self.motion.rotate_right()
                        self.last_turn = "right"
                    else:
                        self.motion.rotate_left()
                        self.last_turn = "left"

                else:
                    if spaces["left"] < spaces["right"]:
                        self.motion.rotate_left()
                        self.last_turn = "left"
                    else:
                        self.motion.rotate_right()
                        self.last_turn = "right"

                time.sleep(0.4)
                self.motion.stop()

                self.state = "SEARCH"

            elif self.state == "SCAN":

                self.motion.stop()

                self.head.move(2, 1800, 0.6)
                time.sleep(0.8)

                self.head.move(2, 1200, 0.6)
                time.sleep(0.8)

                self.head.move(2, 1500, 0.5)

                self.last_scan_time = time.time()
                self.state = "SEARCH"

            elif self.state == "ESCAPE":

                self.motion.stop()
                time.sleep(0.2)

                self.motion.backward()
                time.sleep(0.6)
                self.motion.stop()

                spaces = self.free_space.analyze(frame)

                if spaces["left"] < spaces["right"]:
                    self.motion.rotate_left()
                    self.last_turn = "left"
                else:
                    self.motion.rotate_right()
                    self.last_turn = "right"

                time.sleep(0.8)
                self.motion.stop()

                self.motion.forward()
                self.last_forward_time = time.time()
                time.sleep(1.0)

                self.last_escape_time = time.time()
                self.state = "SEARCH"

            time.sleep(0.05)
