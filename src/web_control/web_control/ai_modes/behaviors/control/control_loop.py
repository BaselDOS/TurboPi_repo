import time
import cv2

from web_control.ai_modes.behaviors.vision.free_space import FreeSpace
from web_control.ai_modes.behaviors.vision.stuck_detector import StuckDetector


class ControlLoop:

    def __init__(self, motion, alerts, get_frame, get_distance, lock):

        self.motion = motion
        self.alerts = alerts

        self.get_frame = get_frame
        self.get_distance = get_distance

        self.lock = lock

        self.free_space = FreeSpace()
        self.stuck_detector = StuckDetector()

        self.state = "SEARCH"
        self.state_start = time.time()

        self.target_detected = False

        self.last_escape_time = 0
        self.escape_cooldown = 3.0  # seconds

    def update_target(self, detected):
        with self.lock:
            self.target_detected = detected

    def run(self):

        while True:

            frame = self.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            # =========================
            # VISION OBSTACLE CHECK (NEW 🔥)
            # =========================
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            h, w = edges.shape
            center = edges[:, w//3:2*w//3]

            center_edges = cv2.countNonZero(center)
            vision_blocked = center_edges > 12000   # tune later

            distance = self.get_distance()

            with self.lock:
                detected = self.target_detected

            # =========================
            # TARGET FOUND
            # =========================
            if detected:
                self.motion.stop()
                time.sleep(0.3)
                self.alerts.beep5()

                with self.lock:
                    self.target_detected = False

                self.state = "SEARCH"
                continue

            # =========================
            # STUCK DETECTION
            # =========================
            if self.stuck_detector.is_stuck(frame) and (time.time() - self.last_escape_time > self.escape_cooldown):
                self.state = "ESCAPE"
                self.state_start = time.time()

            # =========================
            # OBSTACLE (UPDATED 🔥)
            # =========================
            if (distance < 35 or vision_blocked) and self.state != "ESCAPE":
                self.state = "AVOID"
                self.state_start = time.time()

            # =========================
            # STATES
            # =========================

            if self.state == "SEARCH":

                self.motion.forward()
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

            elif self.state == "ESCAPE":

                self.motion.stop()
                time.sleep(0.2)

                # back
                self.motion._send(-0.5, 0.0)
                time.sleep(0.5)
                self.motion.stop()

                # analyze once
                spaces = self.free_space.analyze(frame)

                if spaces["left"] < spaces["right"]:
                    self.motion.rotate_left()
                else:
                    self.motion.rotate_right()

                # hard rotate
                time.sleep(0.7)
                self.motion.stop()

                # forward commit
                self.motion.forward()
                time.sleep(1.5)

                self.last_escape_time = time.time()
                self.state = "SEARCH"

            time.sleep(0.05)
