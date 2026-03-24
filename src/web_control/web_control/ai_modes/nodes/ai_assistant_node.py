#!/usr/bin/env python3
# encoding: utf-8

import os
import time
import threading

import rclpy
from rclpy.node import Node

from ros_robot_controller_msgs.msg import RGBStates

from speech import speech
from speech import awake

from ai_modes.executors.voice_executor import VoiceExecutor
from ai_modes.executors.vision_executor import VisionExecutor


class AIAssistantNode(Node):

    def __init__(self):
        super().__init__("ai_assistant_node")

        print("Initializing AI Assistant Node...")

        # =========================
        # 🔌 PUBLISHERS
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

        # =========================
        # 👁️ VISION NODE
        # =========================
        self.vision_executor = VisionExecutor()

        threading.Thread(
            target=rclpy.spin,
            args=(self.vision_executor,),
            daemon=True
        ).start()

        # =========================
        # 🧠 EXECUTOR
        # =========================
        self.voice_executor = VoiceExecutor(
            rgb_pub=self.rgb_pub,
            sonar_pub=self.sonar_pub,
            logger=self.get_logger()
        )

        # =========================
        # 🎤 WAKE WORD + AUDIO
        # =========================
        port = "/dev/ttyUSB0"
        self.kws = awake.WonderEchoPro(port)

        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model="whisper-1")

        self.tts = speech.RealTimeOpenAITTS()

        # =========================
        # 🔊 AUDIO PATH FIX (IMPORTANT)
        # =========================
        base_path = os.path.dirname(os.path.abspath(__file__))

        self.wakeup_audio = os.path.join(base_path, "../resources/audio/wakeup.wav")
        self.start_audio = os.path.join(base_path, "../resources/audio/start_audio.wav")
        self.no_voice_audio = os.path.join(base_path, "../resources/audio/no_voice.wav")

        # =========================
        # SYSTEM INIT
        # =========================
        try:
            os.system("pinctrl FAN_PWM op dh")
        except:
            pass

        speech.set_volume(80)
        speech.play_audio(self.start_audio)

        print("✅ AI Assistant Node Ready")


    # =========================
    # MODE DETECTION
    # =========================
    def is_vision_request(self, text):

        t = (text or "").lower()

        triggers = [
            "what do you see",
            "describe",
            "look",
            "what is in front",
            "can you see"
        ]

        return any(k in t for k in triggers)


    # =========================
    # MAIN LOOP
    # =========================
    def run(self):

        print("🎤 Waiting for wake word...")
        self.kws.start()

        while True:
            try:
                if self.kws.wakeup():

                    print("🔥 WAKE DETECTED")
                    speech.play_audio(self.wakeup_audio)

                    text = self.asr.asr()

                    if not text:
                        print("No speech detected")
                        speech.play_audio(self.no_voice_audio)
                        continue

                    print("User:", text)

                    # =========================
                    # MODE SWITCH
                    # =========================
                    if self.is_vision_request(text):
                        print("VISION MODE")
                        result = self.vision_executor.describe()
                    else:
                        print("VOICE MODE")
                        result = self.voice_executor.process(text)

                    if not result:
                        result = "I don't know."

                    print("AI:", result)

                    self.tts.tts(result, model="tts-1")

                time.sleep(0.02)

            except KeyboardInterrupt:
                print("Shutting down...")
                break

            except Exception as e:
                print("ERROR:", e)
                time.sleep(0.1)


def main():
    rclpy.init()
    node = AIAssistantNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
