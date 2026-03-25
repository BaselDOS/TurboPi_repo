#!/usr/bin/env python3
# encoding: utf-8

import time
import cv2
import mediapipe as mp

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from speech import speech
from ai_modes.core.config import *


class VisionExecutor(Node):

    def __init__(self):
        super().__init__("vision_executor")

        # =========================
        # CAMERA
        # =========================
        self.bridge = CvBridge()
        self.latest_frame = None

        self.subscription = self.create_subscription(
            Image,
            "/image_raw",
            self.image_callback,
            10
        )

        # =========================
        # VISION (OpenRouter)
        # =========================
        self.client = speech.OpenAIAPI(vllm_api_key, vllm_base_url)
        self.model = "qwen/qwen3.5-flash-02-23"

        # =========================
        # GESTURE SYSTEM
        # =========================
        self.node = None  # injected from AI node

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)

        self.last_gesture = None
        self.last_time = 0

        self.hold_start = None

        self.gesture_sequence = []
        self.seq_time = 0

    # =========================
    def image_callback(self, msg):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding="bgr8"
            )
        except Exception as e:
            print("CV Bridge error:", e)

    # =========================
    # 🔥 KEEP THIS — DO NOT TOUCH
    def describe(self):

        if self.latest_frame is None:
            return "I don't see anything yet."

        print("Sending image to OpenRouter...")

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
    # 🔥 NEW: GESTURE SYSTEM
    def process_gesture(self):

        if self.latest_frame is None or self.node is None:
            return

        frame = self.latest_frame

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            return

        hand = results.multi_hand_landmarks[0]

        gesture = self._detect_gesture(hand)
        if not gesture:
            return

        now = time.time()

        # =========================
        # HOLD STOP
        # =========================
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

        # debounce
        if gesture == self.last_gesture:
            return

        if now - self.last_time < 1.0:
            return

        self.last_time = now
        self.last_gesture = gesture

        print("Gesture:", gesture)

        ve = self.node.voice_executor

        # =========================
        # ACTIONS
        # =========================
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

        # =========================
        # SEQUENCE (dance combo)
        # =========================
        if now - self.seq_time > 2:
            self.gesture_sequence = []

        self.seq_time = now
        self.gesture_sequence.append(gesture)
        self.gesture_sequence = self.gesture_sequence[-3:]

        if self.gesture_sequence == ["two", "two", "fist"]:
            print("DANCE TRIGGERED")
            ve._handle_dance()
            self.gesture_sequence = []

    # =========================
    def _detect_gesture(self, hand):

        tips = [4, 8, 12, 16, 20]

        fingers = []

        fingers.append(hand.landmark[4].x < hand.landmark[3].x)

        for tip in tips[1:]:
            fingers.append(hand.landmark[tip].y < hand.landmark[tip - 2].y)

        thumb, i, m, r, p = fingers

        if thumb and not i and not m and not r and not p:
            return "thumb_up"

        count = sum(fingers)

        if count == 0:
            return "fist"
        if count == 1:
            return "one"
        if count == 2:
            return "two"
        if count == 5:
            return "five"

        return None
