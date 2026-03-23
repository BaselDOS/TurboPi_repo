#!/usr/bin/env python3
# encoding: utf-8

import json
from datetime import datetime
from openai import OpenAI

from ai_modes.core.config import llm_api_key, llm_base_url
from ai_modes.core.color_map import COLOR_MAP, ALLOWED_LED_COLORS
from ai_modes.core.prompts import VOICE_ASSISTANT_PROMPT

from ros_robot_controller_msgs.msg import RGBStates, RGBState


class VoiceExecutor:

    def __init__(self, rgb_pub=None, sonar_pub=None, logger=None):
        # =========================
        # LLM INIT
        # =========================
        self.client = OpenAI(
            api_key=llm_api_key,
            base_url=llm_base_url if llm_base_url else None
        )
        self.model = "gpt-4o-mini"

        # =========================
        # ROS PUBLISHERS
        # =========================
        self.rgb_pub = rgb_pub
        self.sonar_pub = sonar_pub
        self.logger = logger


    # =========================
    # MAIN PROCESS
    # =========================
    def process(self, text: str) -> str:

        text = (text or "").strip()
        if not text:
            return "I did not hear anything."

        self._log("\n=== USER TEXT ===")
        self._log(text)

        today_str = datetime.now().strftime("%Y-%m-%d")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": VOICE_ASSISTANT_PROMPT + f"\n\nDate: {today_str}"
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )

            raw = response.choices[0].message.content or ""

            self._log("\n=== LLM RAW ===")
            self._log(raw)

            data = self._extract_json(raw)

            if not data:
                return "I could not understand that."

            mode = data.get("mode", "chat")
            reply = data.get("reply", "Okay.")
            commands = data.get("commands", [])

            if mode == "command":
                for cmd in commands:
                    if not isinstance(cmd, dict):
                        continue

                    if cmd.get("type") == "led":
                        self._handle_led(cmd.get("value"))

            return reply

        except Exception as e:
            self._log("❌ LLM ERROR:", e)
            return "Something went wrong."


    # =========================
    # JSON PARSER
    # =========================
    def _extract_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except:
            return None


    # =========================
    # LED CONTROL (BOTH SYSTEMS)
    # =========================
    def _handle_led(self, color: str):

        self._log(f"[LED] Requested: {color}")

        if color not in ALLOWED_LED_COLORS:
            self._log(f"❌ Invalid color: {color}")
            return

        if color == "off":
            r, g, b = 0, 0, 0
        else:
            r, g, b = COLOR_MAP[color]

        # ---------- BOARD LED ----------
        if self.rgb_pub:
            try:
                msg = RGBStates()
                msg.states = [
                    RGBState(index=1, red=r, green=g, blue=b),
                    RGBState(index=2, red=r, green=g, blue=b),
                ]
                self.rgb_pub.publish(msg)
                self._log(f"[BOARD LED] → {r},{g},{b}")
            except Exception as e:
                self._log("⚠️ Board LED failed:", e)

        # ---------- SONAR LED ----------
        if self.sonar_pub:
            try:
                msg = RGBStates()
                msg.states = [
                    RGBState(index=0, red=r, green=g, blue=b),
                    RGBState(index=1, red=r, green=g, blue=b),
                ]
                self.sonar_pub.publish(msg)
                self._log(f"[SONAR LED] → {r},{g},{b}")
            except Exception as e:
                self._log("⚠️ Sonar LED failed:", e)

        # fallback
        if not self.rgb_pub and not self.sonar_pub:
            self._log(f"[TEST MODE] RGB: {r},{g},{b}")


    # =========================
    # LOGGER
    # =========================
    def _log(self, *args):
        print(*args)

        if self.logger:
            try:
                self.logger.info(" ".join(str(a) for a in args))
            except:
                pass
