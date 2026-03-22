import rclpy
import threading
import time

from speech import speech
from speech import awake
from executors.voice_executor import VoiceExecutor


class AIAssistantNode:

    def __init__(self):

        print("AI Voice Assistant Running...")

        # ✅ ROS FIRST
        rclpy.init()

        # ✅ Voice + Vision
        self.executor = VoiceExecutor()

        # ✅ ROS spin (vision)
        threading.Thread(
            target=rclpy.spin,
            args=(self.executor.vision,),
            daemon=True
        ).start()

        # ✅ WAKEUP (REAL WAY)
        port = '/dev/ttyUSB0'
        self.kws = awake.WonderEchoPro(port)
        self.kws.start()

        # ✅ ASR + TTS (REAL WAY)
        
        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model='whisper-1')
        self.tts = speech.RealTimeTTS()

    def run(self):
        
        print("Waiting for wake word...")
        while True:
            try: 
                if self.kws.wakeup():   # ✅ REAL wakeup

                    print("Wake word detected")

                    text = self.asr.asr()   # ✅ REAL ASR

                    if not text:
                        print("No speech detected")
                        continue

                    print("User:", text)

                    response = self.executor.process(text)

                    print("AI:", response)

                    self.tts.tts(response)   # ✅ REAL TTS

                time.sleep(0.02)

            except Exception as e:
                print("ERROR:", e)


def main():
    node = AIAssistantNode()
    node.run()


if __name__ == "__main__":
    main()
