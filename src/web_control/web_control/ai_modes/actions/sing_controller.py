import time
import subprocess
from ament_index_python.packages import get_package_share_directory
import os
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

        self.music_proc = None

    # =========================
    def _play_music(self):
        import subprocess
        import os
        from ament_index_python.packages import get_package_share_directory

        try:
            pkg_path = get_package_share_directory("web_control")

            audio_path = os.path.join(
                pkg_path,
                "ai_modes",
                "resources",
                "audio",
                "Chamillionaire_Ridin.wav"
            )

            print("Playing:", audio_path)

            self.music_proc = subprocess.Popen([
                "aplay",
                audio_path
            ])

        except Exception as e:
            print("Audio error:", e)
    # =========================
    def _stop_music(self):
        if self.music_proc:
            self.music_proc.terminate()

    # =========================
    def _move(self, ang_z=0.0, duration=0.4):
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
        time.sleep(1.0)

        # =========================
        # 🔥 LOOP (balanced speed)
        # =========================
        for _ in range(6):

            # LEDs change
            self._led(255, 0, 0)
            self._move(ang_z=1.5, duration=0.4)

            self._led(0, 0, 255)
            self._move(ang_z=-1.5, duration=0.4)

            self._led(0, 255, 0)

            # camera up/down
            self._servo(1, 1300)
            time.sleep(0.15)
            self._servo(1, 1700)
            time.sleep(0.15)

            # camera left/right
            self._servo(2, 1300)
            time.sleep(0.15)
            self._servo(2, 1700)
            time.sleep(0.15)

        # =========================
        # 🔥 finish
        # =========================
        self.cmd_pub.publish(Twist())
        self._led(255, 255, 255)
        self._stop_music()
