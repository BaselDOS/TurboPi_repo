import time
import cv2

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

            # ===== EDGE DETECTION =====
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            h, w = edges.shape
            center = edges[:, w//3:2*w//3]

            center_edges = cv2.countNonZero(center)
            vision_blocked = center_edges > 22000   # less sensitive

            # ===== OBJECT SIZE =====
            boxes = self.get_boxes()
            object_close = False

            for (x1, y1, x2, y2, label) in boxes:
                area = (x2 - x1) * (y2 - y1)

                if area > 45000:   # less sensitive
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

            # ===== STUCK =====
            forwarding = (time.time() - self.last_forward_time) < 0.5
            is_stuck = self.stuck_detector.is_stuck(frame)

            if forwarding and is_stuck and (time.time() - self.last_escape_time > self.escape_cooldown):
                self.state = "ESCAPE"
                self.state_start = time.time()

            # ===== STARTUP PROTECTION =====
            startup = (time.time() - self.start_time) < 2.0

            # ===== OBSTACLE =====
            if not startup and (
                distance < 35 or
                (object_close and self.state == "SEARCH") or
                (vision_blocked and self.state == "SEARCH")
            ) and self.state != "ESCAPE":
                self.state = "AVOID"
                self.state_start = time.time()

            # ===== STATES =====

            if self.state == "SEARCH":

                self.motion.forward()
                self.last_forward_time = time.time()
                time.sleep(0.3)

            elif self.state == "AVOID":

                self.motion.stop()
                time.sleep(0.2)

                spaces = self.free_space.analyze(frame)

                if spaces["left"] < spaces["right"]:
                    self.motion.rotate_left()
                else:
                    self.motion.rotate_right()

                time.sleep(0.6)
                self.motion.stop()

                self.state = "SEARCH"

            elif self.state == "SCAN":

                self.motion.stop()

                # look right
                self.head.move(2, 1800, 0.6)
                time.sleep(0.8)

                # look left
                self.head.move(2, 1200, 0.6)
                time.sleep(0.8)

                # center
                self.head.move(2, 1500, 0.5)

                self.last_scan_time = time.time()
                self.state = "SEARCH"

            elif self.state == "ESCAPE":

                self.motion.stop()
                time.sleep(0.2)

                self.motion.backward()
                time.sleep(0.5)
                self.motion.stop()

                spaces = self.free_space.analyze(frame)

                if spaces["left"] < spaces["right"]:
                    self.motion.rotate_left()
                else:
                    self.motion.rotate_right()

                time.sleep(0.7)
                self.motion.stop()

                self.motion.forward()
                self.last_forward_time = time.time()
                time.sleep(1.5)

                self.last_escape_time = time.time()
                self.state = "SEARCH"

            time.sleep(0.05)
