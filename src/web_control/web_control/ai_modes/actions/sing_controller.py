import time
import subprocess
import threading
from ament_index_python.packages import get_package_share_directory
import os
import wave

from geometry_msgs.msg import Twist
from ros_robot_controller_msgs.msg import (
    RGBStates, RGBState,
    SetPWMServoState, PWMServoState
)


class SingController:

    def __init__(self, cmd_pub, rgb_pub, servo_pub):
        self.cmd_pub = cmd_pub
        self.rgb_pub = rgb_pub
        self.servo_pub = servo_pub

        self.audio_path = None

    # =========================
    def _get_audio_duration(self, path):
        try:
            with wave.open(path, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except Exception as e:
            print("Duration error:", e)
            return 10.0  # fallback

    # =========================
    def _play_music(self):
        try:
            pkg_path = get_package_share_directory("web_control")

            self.audio_path = os.path.join(
                pkg_path,
                "ai_modes",
                "resources",
                "audio",
                "Chamillionaire_Ridin.wav"
            )

            print("Playing:", self.audio_path)

            def run_audio():
                try:
                    subprocess.run(
                        ["aplay", self.audio_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print("Audio error:", e)

            threading.Thread(target=run_audio, daemon=True).start()

        except Exception as e:
            print("Audio error:", e)

    # =========================
    def _move(self, ang_z=0.0, duration=0.3):
        t = Twist()
        t.angular.z = ang_z

        self.cmd_pub.publish(t)
        time.sleep(duration)
        self.cmd_pub.publish(Twist())

    # =========================
    def _led(self, r, g, b):
        msg = RGBStates()
        msg.states = [
            RGBState(index=1, red=r, green=g, blue=b),
            RGBState(index=2, red=r, green=g, blue=b)
        ]
        self.rgb_pub.publish(msg)

    # =========================
    def _servo(self, sid, pos):
        msg = SetPWMServoState()
        s = PWMServoState()
        s.id = [sid]
        s.position = [pos]
        msg.state = [s]
        msg.duration = 0.15
        self.servo_pub.publish(msg)

    # =========================
    def sing(self):

        # 🔥 start music
        self._play_music()

        # 🔥 get duration
        duration = self._get_audio_duration(self.audio_path)
        print("Song duration:", duration)

        start_time = time.time()

        # =========================
        # 🔥 LOOP UNTIL MUSIC ENDS
        # =========================
        while time.time() - start_time < duration:

            # LED + rotate right
            self._led(255, 0, 0)
            self._move(ang_z=1.5, duration=0.3)

            # LED + rotate left
            self._led(0, 0, 255)
            self._move(ang_z=-1.5, duration=0.3)

            # LED green
            self._led(0, 255, 0)

            # camera up/down
            self._servo(1, 1300)
            time.sleep(0.1)
            self._servo(1, 1700)
            time.sleep(0.1)

            # camera left/right
            self._servo(2, 1300)
            time.sleep(0.1)
            self._servo(2, 1700)
            time.sleep(0.1)

        # =========================
        # 🔥 finish
        # =========================
        self.cmd_pub.publish(Twist())
        self._led(255, 255, 255)
