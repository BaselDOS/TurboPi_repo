from speech import speech
from ai_modes.core.config import *
from ai_modes.executors.vision_executor import VisionExecutor


class VoiceExecutor:
    def __init__(self):
        self.llm = speech.OpenAIAPI(llm_api_key, llm_base_url)
        self.vision = VisionExecutor()
        self.model = "gpt-4o-mini"

    def process(self, text: str) -> str:
        text = (text or "").strip()
        text_l = text.lower()

        # ===== Vision trigger =====
        if "see" in text_l or "what do you see" in text_l:
            print("Vision mode activated")
            return self.vision.describe()

        # ===== Normal chat =====
        print("Chat mode activated")

        try:
            response = self.llm.llm(text, prompt="", model=self.model)
            return response

        except Exception as e:
            print("LLM error:", e)
            return "I had a problem answering that."
