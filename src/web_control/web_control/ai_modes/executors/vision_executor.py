#!/usr/bin/env python3
# encoding: utf-8

import time
import cv2
import threading
import mediapipe as mp

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from speech import speech
from web_control.ai_modes.core.config import vllm_api_key, vllm_base_url

from web_control.autonomous.vision.detector import Detector


class VisionExecutor(Node):

    def __init__(self):
        super().__init__("vision_executor")

        # =========================
        # CAMERA
        # =========================
        self.bridge = CvBridge()
        self.latest_frame = None
        self.latest_debug_frame = None

        self.subscription = self.create_subscription(
            Image,
            "/image_raw",
            self.image_callback,
            10
        )

        # =========================
        # 🔥 DEBUG PUBLISHER (NEW)
        # =========================
        self.debug_pub = self.create_publisher(
            Image,
            "/avoidance/debug_image",
            10
        )

        # =========================
        # YOLO DETECTOR
        # =========================
        self.detector = Detector()
        self.latest_boxes = []

        # =========================
        # VISION (OpenRouter)
        # =========================
        self.client = speech.OpenAIAPI(vllm_api_key, vllm_base_url)
        self.model = "qwen/qwen3.5-flash-02-23"

        # =========================
        # LINK BACK TO AI NODE
        # =========================
        self.node = None

        # =========================
        # HAND GESTURES
        # =========================
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

        self.last_gesture = None
        self.last_time = 0.0
        self.hold_start = None
        self.gesture_sequence = []
        self.seq_time = 0.0

        # =========================
        # FACE DETECTION
        # =========================
        self.mp_face = mp.solutions.face_detection
        self.face = self.mp_face.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.6
        )

        # =========================
        # YOLO LOOP
        # =========================
        threading.Thread(target=self.yolo_loop, daemon=True).start()

    # =========================
    def publish_debug(self, frame):
        try:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.debug_pub.publish(msg)
        except Exception as e:
            print("Debug publish error:", e)

    # =========================
    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding="bgr8"
            )
            self.latest_frame = frame

            if self.latest_debug_frame is None:
                self.latest_debug_frame = frame.copy()

        except Exception as e:
            print("CV Bridge error:", e)

    # =========================
    def yolo_loop(self):
        while True:
            try:
                if self.latest_frame is not None:
                    self.process_yolo()
            except Exception as e:
                print("YOLO error:", e)

            time.sleep(0.03)

    # =========================
    def process_yolo(self):

        frame = self.latest_frame.copy()

        boxes, found = self.detector.detect(frame)

        self.latest_boxes = boxes

        for (x1, y1, x2, y2, label) in boxes:
            if label == "sports ball":
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0,255,0),
                    2
                )

        self.latest_debug_frame = frame
        self.publish_debug(frame)  # 🔥 NEW

    # =========================
    def describe(self):

        if self.latest_frame is None:
            return "I don't see anything yet."

        print("Sending image to vision model...")

        try:
            result = self.client.vllm(
                "",
                self.latest_frame,
                prompt="Describe what you see in the image",
                model=self.model
            )
            return result

        except Exception as e:
            print("Vision error:", e)
            return "Vision processing failed."

    # =========================
    def process_face(self):

        if self.latest_frame is None:
            return

        frame = self.latest_frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face.process(rgb)

        found_face = False

        if results.detections:
            h, w = frame.shape[:2]

            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box

                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                bw = int(bbox.width * w)
                bh = int(bbox.height * h)

                x = max(0, x)
                y = max(0, y)
                bw = max(1, bw)
                bh = max(1, bh)

                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    "FACE",
                    (x, max(20, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                found_face = True

        if found_face:
            cv2.putText(frame, "FACE MODE", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        else:
            cv2.putText(frame, "FACE MODE - NO FACE", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

        self.latest_debug_frame = frame
        self.publish_debug(frame)  # 🔥 NEW

    # =========================
    def process_gesture(self):

        if self.latest_frame is None or self.node is None:
            return

        frame = self.latest_frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            cv2.putText(frame, "GESTURE MODE - NO HAND", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            self.latest_debug_frame = frame
            self.publish_debug(frame)  # 🔥 NEW
            return

        hand = results.multi_hand_landmarks[0]
        self.mp_draw.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)

        gesture = self._detect_gesture(hand)

        if gesture:
            cv2.putText(frame, f"GESTURE: {gesture}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        else:
            cv2.putText(frame, "GESTURE MODE", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

        self.latest_debug_frame = frame
        self.publish_debug(frame)  # 🔥 NEW

        if not gesture:
            return

        now = time.time()

        if gesture == self.last_gesture:
            if self.hold_start is None:
                self.hold_start = now

            if now - self.hold_start > 2.0:
                print("STOP TRIGGERED")
                self.node.voice_executor.stop_all()
                self.hold_start = None
                return
        else:
            self.hold_start = None

        if gesture == self.last_gesture and (now - self.last_time) < 0.5:
            return

        if now - self.last_time < 0.5:
            return

        self.last_time = now
        self.last_gesture = gesture

        print("Gesture:", gesture)

        ve = self.node.voice_executor

        if gesture == "one":
            ve._handle_move("forward", 1)

        elif gesture == "two":
            ve._handle_move("backward", 1)

        elif gesture == "fist":
            ve._handle_buzzer(2)

        elif gesture == "five":
            ve._handle_camera("look_up")

        elif gesture == "thumb_up":
            ve._handle_dance()
