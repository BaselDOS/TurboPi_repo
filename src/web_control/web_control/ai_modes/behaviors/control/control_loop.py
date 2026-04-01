import time
import cv2

from web_control.ai_modes.behaviors.vision.vision_detector import VisionDetector
from web_control.ai_modes.behaviors.vision.optical_flow import OpticalFlowDetector
from web_control.ai_modes.behaviors.control.motion_controller import MotionController


class ControlLoop:

    def __init__(self, motion, alerts, head, get_frame, get_distance, get_boxes, lock):

        self.motion = motion
        self.alerts = alerts
        self.head = head

        self.get_frame = get_frame
        self.get_distance = get_distance
        self.get_boxes = get_boxes

        self.lock = lock

        # ===== CORE (FROM AVOIDANCE NODE) =====
        self.vision = VisionDetector()
        self.flow = OpticalFlowDetector()
        self.controller = MotionController()

        self.target_detected = False

        # scan behavior
        self.last_scan = 0
        self.scan_interval = 5.0

    # =========================
    def update_target(self, detected):
        with self.lock:
            self.target_detected = detected

    # =========================
    def run(self):

        while True:

            frame = self.get_frame()
            if frame is None:
                time.sleep(0.02)
                continue

            distance = self.get_distance()

            with self.lock:
                detected = self.target_detected

            # =========================
            # 🎯 TARGET FOUND
            # =========================
            if detected:
                self.motion.stop()
                time.sleep(0.2)

                self.alerts.beep5()

                with self.lock:
                    self.target_detected = False

                continue

            # =========================
            # 🧠 VISION + FLOW (LIKE AVOIDANCE NODE)
            # =========================
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow_val = self.flow.compute(gray)

            left, center, right = self.vision.detect(frame)

            # =========================
            # 🧠 DECISION (THE REAL FIX)
            # =========================
            lin_x, lin_y, ang_z = self.controller.decide(
                left,
                center,
                right,
                flow_val,
                distance
            )

            # =========================
            # 🚗 MOVE
            # =========================
            self.motion._send(float(lin_x),float( ang_z))

            # =========================
            # 🔍 SCAN (CONTROLLED, NOT CHAOTIC)
            # =========================
            if time.time() - self.last_scan > self.scan_interval:

                self.motion.stop()

                self.head.move(2, 1800, 0.5)
                time.sleep(0.5)

                self.head.move(2, 1200, 0.5)
                time.sleep(0.5)

                self.head.move(2, 1500, 0.3)

                self.last_scan = time.time()

            time.sleep(0.05)
