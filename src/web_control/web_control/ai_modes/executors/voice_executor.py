#!/usr/bin/env python3
# encoding: utf-8

import json
import time
from datetime import datetime
from openai import OpenAI

from ai_modes.core.config import llm_api_key, llm_base_url
from ai_modes.core.color_map import COLOR_MAP, ALLOWED_LED_COLORS
from ai_modes.core.prompts import VOICE_ASSISTANT_PROMPT

from geometry_msgs.msg import Twist
from ros_robot_controller_msgs.msg import (
    RGBStates, RGBState,
    SetPWMServoState, PWMServoState,
    BuzzerState
)


class VoiceExecutor:

    def __init__(self,
                 rgb_pub=None,
                 sonar_pub=None,
                 logger=None,
                 cmd_pub=None,
                 servo_pub=None,
                 buzzer_pub=None):

        self.client = OpenAI(
            api_key=llm_api_key,
            base_url=llm_base_url if llm_base_url else None
        )
        self.model = "gpt-4o-mini"

        self.rgb_pub = rgb_pub
        self.sonar_pub = sonar_pub
        self.cmd_pub = cmd_pub
        self.servo_pub = servo_pub
        self.buzzer_pub = buzzer_pub
        self.logger = logger

    # =========================
    def process(self, text: str) -> str:

        text = (text or "").strip()
        if not text:
            return "I did not hear anything."

        today = datetime.now().strftime("%Y-%m-%d")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": VOICE_ASSISTANT_PROMPT + f"\nDate: {today}"},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )

        raw = response.choices[0].message.content or ""
        print("LLM RAW:", raw)

        data = self._extract_json(raw)
        if not data:
            return "I did not understand."

        reply = data.get("reply", "Okay.")
        commands = data.get("commands", [])

        for cmd in commands:
            t = cmd.get("type")

            if t == "move":
                self._handle_move(
                    cmd.get("value"),
                    cmd.get("duration", 1.5)
                )

            elif t == "camera":
                self._handle_camera(cmd.get("value"))

            elif t == "buzzer":
                self._handle_buzzer(cmd.get("count", 1))

            elif t == "led":
                self._handle_led(cmd.get("value"))

        return reply

    # =========================
    def _extract_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except:
            return None

    # =========================
    def _handle_move(self, direction, duration=1.5):
        if not self.cmd_pub:
            return

        t = Twist()

        if direction == "forward":
            t.linear.x = 0.3
        elif direction == "backward":
            t.linear.x = -0.3
        elif direction == "left":
            t.linear.y = 0.3
        elif direction == "right":
            t.linear.y = -0.3
        elif direction == "turn_left":
            t.angular.z = 1.0
        elif direction == "turn_right":
            t.angular.z = -1.0
        else:
            return

        self.cmd_pub.publish(t)
        time.sleep(duration)
        self.cmd_pub.publish(Twist())

    # =========================
    def _handle_camera(self, action):
        if not self.servo_pub:
            return

        if action == "look_up":
            servo_id, pos = 1, 1300
        elif action == "look_down":
            servo_id, pos = 1, 1700
        elif action == "look_left":
            servo_id, pos = 2, 1700
        elif action == "look_right":
            servo_id, pos = 2, 1300
        else:
            return

        msg = SetPWMServoState()
        s = PWMServoState()
        s.id = [servo_id]
        s.position = [pos]
        msg.state = [s]
        msg.duration = 0.2

        self.servo_pub.publish(msg)

    # =========================
    def _handle_buzzer(self, count=1):
        if not self.buzzer_pub:
            return

        for _ in range(count):
            msg = BuzzerState()
            msg.freq = 2000
            msg.on_time = 0.2
            msg.off_time = 0.01
            msg.repeat = 1

            self.buzzer_pub.publish(msg)
            time.sleep(0.3)

    # =========================
    def _handle_led(self, color):

        if color not in ALLOWED_LED_COLORS:
            return

        if color == "off":
            r, g, b = 0, 0, 0
        else:
            r, g, b = COLOR_MAP[color]

        if self.rgb_pub:
            msg = RGBStates()
            msg.states = [
                RGBState(index=1, red=r, green=g, blue=b),
                RGBState(index=2, red=r, green=g, blue=b),
            ]
            self.rgb_pub.publish(msg)

        if self.sonar_pub:
            msg = RGBStates()
            msg.states = [
                RGBState(index=0, red=r, green=g, blue=b),
                RGBState(index=1, red=r, green=g, blue=b),
            ]
            self.sonar_pub.publish(msg)
