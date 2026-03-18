import requests
import json
from .ai_prompt import PROMPT

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = "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"

def ask_ai(text):

    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {"role":"system","content":PROMPT},
            {"role":"user","content":text}
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":"application/json"
    }

    r = requests.post(API_URL, headers=headers, json=payload)

    content = r.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(content)
    except:
        return {"commands":[]}
