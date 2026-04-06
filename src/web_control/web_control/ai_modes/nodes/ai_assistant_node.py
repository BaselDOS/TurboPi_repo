#!/usr/bin/env python3
# encoding: utf-8

import os
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
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

        self.ui_state = "IDLE"

        # 🔥 SINGLE TASK CONTROL
        self.current_task_thread = None
        self.stop_flag = False

        # =========================
        # PUBLISHERS
        # =========================
        self.rgb_pub = self.create_publisher(RGBStates, "/ros_robot_controller/set_rgb", 10)
        self.sonar_pub = self.create_publisher(RGBStates, "/sonar_controller/set_rgb", 10)
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.servo_pub = self.create_publisher(SetPWMServoState, "/ros_robot_controller/pwm_servo/set_state", 10)
        self.buzzer_pub = self.create_publisher(BuzzerState, "/ros_robot_controller/set_buzzer", 10)

        # =========================
        # SUBSCRIBER
        # =========================
        self.create_subscription(String, "/voice_commands", self.ui_voice_callback, 10)

        # =========================
        # EXECUTORS
        # =========================
        self.vision_executor = VisionExecutor()
        self.vision_executor.node = self

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
        self.asr.update_session(model="gpt-4o-mini-transcribe")

        self.tts = speech.RealTimeOpenAITTS()

        pkg_path = get_package_share_directory('web_control')
        audio_path = os.path.join(pkg_path, 'ai_modes', 'resources', 'audio')

        self.wakeup_audio = os.path.join(audio_path, 'wakeup.wav')
        self.start_audio = os.path.join(audio_path, 'start_audio.wav')

        speech.set_volume(80)
        speech.play_audio(self.start_audio)

    # =========================
    def stop_current_task(self):
        print("Stopping current task...")

        self.stop_flag = True

        try:
            speech.stop_audio()
        except:
            pass

        self.cmd_pub.publish(Twist())

        if self.current_task_thread and self.current_task_thread.is_alive():
            self.current_task_thread.join(timeout=0.5)

        self.stop_flag = False

    # =========================
    def run_task(self, text):
        def task():
            if self.stop_flag:
                return

            print("Processing:", text)

            if self.is_vision_request(text):
                result = self.vision_executor.describe()
            else:
                result = self.voice_executor.process(text)

            if self.stop_flag:
                return

            if not result:
                result = "I don't know."

            print("AI:", result)
            self.tts.tts(result)

        t = threading.Thread(target=task, daemon=True)
        self.current_task_thread = t
        t.start()

    # =========================
    def is_vision_request(self, text):
        t = (text or "").lower()
        return any(k in t for k in [
            "what do you see",
            "describe what you see",
            "what is in front of you"
        ])

    # =========================
    def is_wake_word(self, text):
        return any(v in text for v in ["dos", "dose", "dios"])

    # =========================
    def ui_voice_callback(self, msg):
        text = (msg.data or "").strip().lower()
        if not text:
            return

        print(f"[UI] {self.ui_state} → {text}")

        if self.ui_state == "IDLE":
            if self.is_wake_word(text):
                print("Wake detected")
                self.ui_state = "LISTENING"
                speech.play_audio(self.wakeup_audio)
                self.tts.tts("I am ready")
            return

        if self.ui_state == "LISTENING":
            self.stop_current_task()
            self.run_task(text)

    # =========================
    def run(self):
        self.kws.start()
        while True:
            time.sleep(0.5)


def main():
    rclpy.init()

    node = AIAssistantNode()

    threading.Thread(target=node.run, daemon=True).start()

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.add_node(node.vision_executor)

    executor.spin()


if __name__ == "__main__":
    main()
