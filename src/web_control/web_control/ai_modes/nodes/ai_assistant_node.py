import rclpy
import threading
import time

from speech import speech
from speech import awake
from ai_modes.executors.voice_executor import VoiceExecutor


class AIAssistantNode:
    def __init__(self):
        print("AI Voice Assistant Running...")

        rclpy.init()

        self.executor = VoiceExecutor()

        # Run vision node in background
        threading.Thread(
            target=rclpy.spin,
            args=(self.executor.vision,),
            daemon=True
        ).start()

        # Wake word
        port = "/dev/ttyUSB0"
        self.kws = awake.WonderEchoPro(port)
        self.kws.start()

        # ASR (OpenAI)
        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model="whisper-1")

        # TTS (OpenAI)
        self.tts = speech.RealTimeOpenAITTS()

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

                    response = self.executor.process(text)

                    if not response:
                        response = "Sorry, I could not process that."

                    print("AI:", response)

                    self.tts.tts(response, model="tts-1")

                time.sleep(0.02)

            except KeyboardInterrupt:
                print("Shutting down...")
                try:
                    self.kws.exit()
                except:
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
