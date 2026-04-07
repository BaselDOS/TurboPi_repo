#!/usr/bin/env python3
# encoding: utf-8

import json
import os
import signal
import subprocess
import threading
import time
from datetime import datetime

from openai import OpenAI

from web_control.ai_modes.core.config import llm_api_key, llm_base_url
from web_control.ai_modes.core.color_map import COLOR_MAP, ALLOWED_LED_COLORS
from web_control.ai_modes.core.prompts import VOICE_ASSISTANT_PROMPT
from web_control.ai_modes.actions.sing_controller import SingController
from web_control.ai_modes.actions.dance_controller import DanceController

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

        self.dance = DanceController(
            cmd_pub=self.cmd_pub,
            rgb_pub=self.rgb_pub,
            servo_pub=self.servo_pub,
            buzzer_pub=self.buzzer_pub
        )

        self.sing = SingController(
            cmd_pub=self.cmd_pub,
            rgb_pub=self.rgb_pub,
            servo_pub=self.servo_pub
        )

        self.current_process = None
        self.current_mode = "chat"
        self.process_lock = threading.Lock()

        self.is_processing = False
        self.last_command_time = 0
        self.last_command_text = None

    # =========================
    def process(self, text: str) -> str:

        text = (text or "").strip()
        if not text:
            return "I did not hear anything."

        now = time.time()

        if self.is_processing:
            return ""

        if text == self.last_command_text:
            return ""

        if now - self.last_command_time < 1.0:
            return ""

        self.is_processing = True
        self.last_command_time = now
        self.last_command_text = text

        try:
            today = datetime.now().strftime("%Y-%m-%d")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": VOICE_ASSISTANT_PROMPT + f"\nDate: {today}"
                    },
                    {
                        "role": "user",
                        "content": text
                    },
                ],
                temperature=0,
            )

            raw = response.choices[0].message.content or ""
            data = self._extract_json(raw)

            if not data:
                return "I did not understand."

            reply = data.get("reply", "Okay.")
            commands = data.get("commands", [])

            for cmd in commands:
                self._execute_command(cmd)

            return reply

        finally:
            self.is_processing = False

    # =========================
    def _execute_command(self, cmd):
        t = (cmd.get("type") or "").strip()

        if t == "move":
            self._handle_move(cmd.get("value"), cmd.get("duration", 1.5))

        elif t == "camera":
            self._handle_camera(cmd.get("value"))

        elif t == "buzzer":
            self._handle_buzzer(cmd.get("count", 1))

        elif t == "led":
            self._handle_led(cmd.get("value"))

        elif t == "dance":
            self._handle_dance()

        elif t == "sing":
            self._handle_sing()

        elif t == "avoidance":
            self._handle_avoidance()

        elif t == "scan":
            self._handle_scan()

        elif t == "vision_mode":
            self._stop_autonomous_process()
            self.current_mode = cmd.get("value", "idle")

    # =========================
    def _extract_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except Exception:
            return None

    # =========================
    def _publish_stop(self):
        if self.cmd_pub:
            self.cmd_pub.publish(Twist())

    # =========================
    def stop_all(self):
        self._stop_autonomous_process()
        self._publish_stop()
        self._handle_led("off")

        # 🔥 RESTORE VISION + FORCE STREAM
        if hasattr(self, "node") and self.node:
            ve = self.node.vision_executor
            ve.active = True

            # 🔥 FORCE STREAM TO UPDATE (CRITICAL FIX)
            for _ in range(5):
                if ve.latest_frame is not None:
                    ve.publish_debug(ve.latest_frame.copy()) 

    # =========================
    def _stop_autonomous_process(self):
        with self.process_lock:
            proc = self.current_process
            if not proc:
                return

            try:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGINT)
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass

            self.current_process = None
            self.current_mode = "chat"
            time.sleep(0.1)

    # =========================
    def _start_autonomous_process(self, command, mode_name):
        self.stop_all()

        try:
            self.current_process = subprocess.Popen(
                command,
                start_new_session=True
            )
            self.current_mode = mode_name
        except Exception as e:
            self.current_process = None
            self.current_mode = "chat"
            print(f"Failed to start {mode_name}: {e}")

    # =========================
    def _handle_move(self, direction, duration=1.5):

        if not self.cmd_pub:
            return

        direction = (direction or "").strip().lower()

        mapping = {
            "forward": "forward",
            "back": "backward",
            "backward": "backward",
            "left": "left",
            "right": "right",
            "turn left": "turn_left",
            "turn right": "turn_right",
            "rotate left": "turn_left",
            "rotate right": "turn_right",
        }

        direction = mapping.get(direction, direction)

        if direction == "stop":
            self.stop_all()
            return

        try:
            duration = float(duration)
        except Exception:
            duration = 1.5

        self._stop_autonomous_process()

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
            t.angular.z = 2.0
        elif direction == "turn_right":
            t.angular.z = -2.0
        else:
            print("UNKNOWN MOVE:", direction)
            return

        self.cmd_pub.publish(t)
        time.sleep(duration)
        self._publish_stop()

    # =========================
    def _handle_camera(self, action):
        if not self.servo_pub:
            return

        self._stop_autonomous_process()

        action = (action or "").strip().lower()

        if action == "look_up":
            sid, pos = 1, 1300

        elif action == "look_down":
            sid, pos = 1, 1700

        elif action == "look_left":
            sid, pos = 2, 1700

        elif action == "look_right":
            sid, pos = 2, 1300

        elif action == "look_center":
            msg = SetPWMServoState()

            s1 = PWMServoState()
            s1.id = [1]
            s1.position = [1500]

            s2 = PWMServoState()
            s2.id = [2]
            s2.position = [1500]

            msg.state = [s1, s2]
            msg.duration = 0.3

            self.servo_pub.publish(msg)
            return

        else:
            return

        msg = SetPWMServoState()
        s = PWMServoState()
        s.id = [sid]
        s.position = [pos]
        msg.state = [s]
        msg.duration = 0.2

        self.servo_pub.publish(msg)

    # =========================
    def _handle_buzzer(self, count=1):

        if not self.buzzer_pub:
            return

        for _ in range(int(count)):
            msg = BuzzerState()
            msg.freq = 2000
            msg.on_time = 0.2
            msg.off_time = 0.2
            msg.repeat = 1

            self.buzzer_pub.publish(msg)
            time.sleep(0.4)

    # =========================
    def _handle_led(self, color):

        if not color:
            return

        color = color.strip().lower()

        if color not in ALLOWED_LED_COLORS:
            return

        if color == "off":
            r, g, b = 0, 0, 0
        else:
            r, g, b = COLOR_MAP[color]

        board_msg = RGBStates()
        board_msg.states = [
            RGBState(index=1, red=r, green=g, blue=b),
            RGBState(index=2, red=r, green=g, blue=b),
        ]

        sonar_msg = RGBStates()
        sonar_msg.states = [
            RGBState(index=0, red=r, green=g, blue=b),
            RGBState(index=1, red=r, green=g, blue=b),
        ]

        if self.rgb_pub:
            self.rgb_pub.publish(board_msg)

        if self.sonar_pub:
            self.sonar_pub.publish(sonar_msg)

    # =========================
    def _handle_dance(self):
        self._stop_autonomous_process()
        threading.Thread(target=self.dance.fun_dance, daemon=True).start()

    # =========================
    def _handle_sing(self):
        self._stop_autonomous_process()
        threading.Thread(target=self.sing.sing, daemon=True).start()

    # =========================
    def _handle_avoidance(self):
        self._start_autonomous_process(
            ["ros2", "run", "web_control", "avoidance_node"],
            "avoidance"
        )

    # =========================
    def _handle_scan(self):
        self._start_autonomous_process(
            ["ros2", "run", "web_control", "scan_and_find_node"],
            "scan"
        )
