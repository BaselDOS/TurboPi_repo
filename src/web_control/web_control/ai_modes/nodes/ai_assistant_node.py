import rclpy
import threading
import time

from speech import speech
from speech import awake

from ai_modes.executors.voice_executor import VoiceExecutor
from ai_modes.executors.vision_executor import VisionExecutor


class AIAssistantNode:
    def __init__(self):
        print("AI Voice Assistant Running...")

        rclpy.init()

        self.voice_executor = VoiceExecutor()
        self.vision_executor = VisionExecutor()

        threading.Thread(
            target=rclpy.spin,
            args=(self.vision_executor,),
            daemon=True
        ).start()

        port = "/dev/ttyUSB0"
        self.kws = awake.WonderEchoPro(port)
        self.kws.start()

        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model="whisper-1")

        self.tts = speech.RealTimeOpenAITTS()

    def is_vision_request(self, text: str) -> bool:
        t = (text or "").lower()
        vision_triggers = [
            "what do you see",
            "what can you see",
            "describe the image",
            "describe what you see",
            "look at this",
            "what is in front of you",
            "can you see",
        ]
        return any(trigger in t for trigger in vision_triggers)

    def run(self):
        print("Waiting for wake word...")

        while True:
            try:
                if self.kws.wakeup():
                    print("Wake word detected")

                    text = self.asr.asr()

                    if not text:
                        print("No speech detected")
                        continue

                    print("User:", text)

                    if self.is_vision_request(text):
                        print("Vision mode activated")
                        result = self.vision_executor.describe()
                    else:
                        print("Voice/chat/command mode activated")
                        result = self.voice_executor.process(text)

                    if not result:
                        result = "Sorry, I could not process that."

                    print("AI:", result)
                    self.tts.tts(result, model="tts-1")

                time.sleep(0.02)

            except KeyboardInterrupt:
                print("Shutting down...")
                try:
                    self.kws.exit()
                except Exception:
                    pass
                break

            except Exception as e:
                print("ERROR:", e)
                time.sleep(0.1)


def main():
    node = AIAssistantNode()
    node.run()


if __name__ == "__main__":
    main()
