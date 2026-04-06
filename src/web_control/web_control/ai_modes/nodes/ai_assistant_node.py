#!/usr/bin/env python3
# encoding: utf-8

import os
import time
import threading

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from std_msgs.msg import String

from geometry_msgs.msg import Twist
from ros_robot_controller_msgs.msg import (
    RGBStates,
    SetPWMServoState,
    BuzzerState
)

from speech import speech, awake

from web_control.ai_modes.executors.voice_executor import VoiceExecutor
from web_control.ai_modes.executors.vision_executor import VisionExecutor


class AIAssistantNode(Node):

    def __init__(self):
        super().__init__("ai_assistant_node")

        print("Initializing AI Assistant Node...")

        self.vision_mode = "idle"

        # =========================
        # STATE MACHINE (NEW)
        # =========================
        self.ui_state = "IDLE"
        self.last_interaction_time = time.time()
        self.timeout_sec = 5

        # =========================
        # PUBLISHERS
        # =========================
        self.rgb_pub = self.create_publisher(
            RGBStates,
            "/ros_robot_controller/set_rgb",
            10
        )

        self.sonar_pub = self.create_publisher(
            RGBStates,
            "/sonar_controller/set_rgb",
            10
        )

        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.servo_pub = self.create_publisher(
            SetPWMServoState,
            "/ros_robot_controller/pwm_servo/set_state",
            10
        )

        self.buzzer_pub = self.create_publisher(
            BuzzerState,
            "/ros_robot_controller/set_buzzer",
            10
        )

        # =========================
        # UI VOICE SUBSCRIBER
        # =========================
        self.create_subscription(
            String,
            "/voice_commands",
            self.ui_voice_callback,
            10
        )

        # =========================
        # VISION EXECUTOR
        # =========================
        self.vision_executor = VisionExecutor()
        self.vision_executor.node = self

        threading.Thread(
            target=rclpy.spin,
            args=(self.vision_executor,),
            daemon=True
        ).start()

        # =========================
        # VOICE EXECUTOR
        # =========================
        self.voice_executor = VoiceExecutor(
            rgb_pub=self.rgb_pub,
            sonar_pub=self.sonar_pub,
            logger=self.get_logger(),
            cmd_pub=self.cmd_pub,
            servo_pub=self.servo_pub,
            buzzer_pub=self.buzzer_pub
        )
        self.voice_executor.node = self

        # =========================
        # AUDIO
        # =========================
        port = "/dev/ttyUSB0"
        self.kws = awake.WonderEchoPro(port)

        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model="gpt-4o-mini")

        self.tts = speech.RealTimeOpenAITTS()

        pkg_path = get_package_share_directory('web_control')
        audio_path = os.path.join(pkg_path, 'ai_modes', 'resources', 'audio')

        self.wakeup_audio = os.path.join(audio_path, 'wakeup.wav')
        self.start_audio = os.path.join(audio_path, 'start_audio.wav')
        self.no_voice_audio = os.path.join(audio_path, 'no_voice.wav')

        speech.set_volume(80)
        speech.play_audio(self.start_audio)

        print("AI Assistant Ready")

    # =========================
    def is_vision_request(self, text):
        t = (text or "").lower()

        triggers = [
            "what do you see",
            "describe what you see",
            "what is in front of you",
            "can you see"
        ]

        return any(k in t for k in triggers)

    # =========================
    def run(self):

        print("Waiting for wake word...")
        self.kws.start()

        while True:
            try:
                if self.vision_mode == "gesture":
                    self.vision_executor.process_gesture()

                elif self.vision_mode == "face":
                    self.vision_executor.process_face()

                if self.kws.wakeup():

                    speech.play_audio(self.wakeup_audio)

                    text = self.asr.asr()

                    if not text:
                        speech.play_audio(self.no_voice_audio)
                        continue

                    print("User:", text)

                    if self.is_vision_request(text):
                        result = self.vision_executor.describe()
                    else:
                        result = self.voice_executor.process(text)

                    if not result:
                        result = "I don't know."

                    print("AI:", result)

                    self.tts.tts(result)

                time.sleep(0.5)

            except Exception as e:
                print("ERROR:", e)
                time.sleep(0.1)

    # =========================
    # 🔥 FIXED UI FLOW (STATE MACHINE)
    # =========================
    def ui_voice_callback(self, msg):
        text = (msg.data or "").strip().lower()
        if not text:
            return

        print(f"[UI] State={self.ui_state} | Text={text}")

        now = time.time()

        try:
            # =========================
            # TIMEOUT
            # =========================
            if self.ui_state == "LISTENING":
                if now - self.last_interaction_time > self.timeout_sec:
                    print("Timeout → back to IDLE")
                    self.ui_state = "IDLE"

            # =========================
            # STATE: IDLE
            # =========================
            if self.ui_state == "IDLE":

                if "turbopi" in text:
                    print("Wake word detected (UI)")

                    self.ui_state = "LISTENING"
                    self.last_interaction_time = now

                    speech.play_audio(self.wakeup_audio)
                    self.tts.tts("I am ready")

                else:
                    print("Ignored (no wake word)")

                return

            # =========================
            # STATE: LISTENING
            # =========================
            if self.ui_state == "LISTENING":

                self.ui_state = "PROCESSING"

                print("Processing command...")

                if self.is_vision_request(text):
                    result = self.vision_executor.describe()
                else:
                    result = self.voice_executor.process(text)

                if not result:
                    result = "I don't know."

                print("AI:", result)
                self.tts.tts(result)

                self.ui_state = "IDLE"
                return

        except Exception as e:
            print("ERROR (UI voice):", e)
            self.ui_state = "IDLE"


def main():
    rclpy.init()
    node = AIAssistantNode()
    node.run()


if __name__ == "__main__":
    main()
