import json
from datetime import datetime

from openai import OpenAI

from ai_modes.core.config import llm_api_key
from ai_modes.core.color_map import COLOR_MAP, ALLOWED_LED_COLORS
from ai_modes.core.prompts import VOICE_ASSISTANT_PROMPT


def extract_json(text: str):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end <= 0:
            return None
        return json.loads(text[start:end])
    except Exception:
        return None


class VoiceExecutor:
    def __init__(self):
        self.client = OpenAI(api_key=llm_api_key)
        self.model = "gpt-4o-mini"

    def process(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "I did not hear anything."

        print("\n=== USER TEXT ===")
        print(text)

        today_str = datetime.now().strftime("%Y-%m-%d")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            VOICE_ASSISTANT_PROMPT
                            + f"\n\nCurrent local date: {today_str}\n"
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )

            raw = response.choices[0].message.content or ""

            print("\n=== LLM RAW ===")
            print(raw)

            data = extract_json(raw)
            if not data:
                print("❌ Failed to parse JSON")
                return "I could not understand that."

            mode = data.get("mode", "chat")
            reply = data.get("reply", "Okay.")
            commands = data.get("commands", [])

            if not isinstance(commands, list):
                print("❌ commands is not a list")
                return "Invalid command format."

            if mode == "command":
                for cmd in commands:
                    if not isinstance(cmd, dict):
                        continue

                    cmd_type = cmd.get("type")
                    value = cmd.get("value")

                    if cmd_type == "led":
                        self.handle_led(value)

            return reply

        except Exception as e:
            print("❌ LLM ERROR:", e)
            return "I had a problem processing that."

    def handle_led(self, color: str):
        print(f"[LED] Requested: {color}")

        if color not in ALLOWED_LED_COLORS:
            print(f"❌ Invalid LED color from AI: {color}")
            return

        if color == "off":
            r, g, b = 0, 0, 0
        else:
            r, g, b = COLOR_MAP[color]

        try:
            from hiwonder import Board

            # Change both pixels if your board uses 2 onboard RGB LEDs
            Board.RGB.setPixelColor(0, Board.PixelColor(r, g, b))
            Board.RGB.setPixelColor(1, Board.PixelColor(r, g, b))
            Board.RGB.show()

            print(f"[LED] Applied RGB: {r}, {g}, {b}")

        except Exception as e:
            print("⚠️ LED hardware call failed:", e)
            print(f"[LED] TEST MODE RGB: {r}, {g}, {b}")
