from speech import speech
from core.config import *
from executors.vision_executor import VisionExecutor

class VoiceExecutor:

    def __init__(self):
        self.llm = speech.OpenAIAPI(llm_api_key, llm_base_url)
        self.vision = VisionExecutor()

    def process(self, text):

        # ===== VISION MODE =====
        if "see" in text or "what do you see" in text:
            print("Vision mode activated")
            return self.vision.describe()

        # ===== NORMAL CHAT =====
        return self.llm.chat(text)

    def speak(self, text):
        print("Speaking:", text)
        speech.tts(text)   # ✅ FUNCTION, not class
