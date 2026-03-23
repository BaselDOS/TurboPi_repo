from core.config import *
from speech import speech

class LLMProvider:
    def __init__(self):
        self.client = speech.OpenAIAPI(llm_api_key, llm_base_url)
        self.model = "gpt-4o-mini"

    def ask(self, text):
        return self.client.llm(text, model=self.model)
