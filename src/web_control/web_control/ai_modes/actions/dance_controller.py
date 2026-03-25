import time
from geometry_msgs.msg import Twist
from ros_robot_controller_msgs.msg import (
    RGBStates, RGBState,
    SetPWMServoState, PWMServoState,
    BuzzerState
)


class DanceController:

    def __init__(self, cmd_pub, rgb_pub, servo_pub, buzzer_pub):
        self.cmd_pub = cmd_pub
        self.rgb_pub = rgb_pub
        self.servo_pub = servo_pub
        self.buzzer_pub = buzzer_pub

    # =========================
    def _move(self, lin_x=0.0, lin_y=0.0, ang_z=0.0, duration=0.4):
        t = Twist()
        t.linear.x = lin_x
        t.linear.y = lin_y
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
    def _beep(self, freq=2000, dur=0.08):
        msg = BuzzerState()
        msg.freq = freq
        msg.on_time = dur
        msg.off_time = 0.01
        msg.repeat = 1
        self.buzzer_pub.publish(msg)

    # =========================
    def _beat(self):
        """🔥 simple rhythm pattern"""
        self._beep(1800, 0.06)
        time.sleep(0.08)
        self._beep(2400, 0.06)

    # =========================
    def fun_dance(self):

        # =========================
        # 🔥 INTRO (build up)
        # =========================
        for i in range(3):
            self._led(255, 0, 0)
            self._beep(1500, 0.05)
            time.sleep(0.1)

            self._led(0, 0, 255)
            self._beep(2000, 0.05)
            time.sleep(0.1)

        # =========================
        # 🔥 MAIN LOOP (groove)
        # =========================
        for _ in range(4):

            # left hit
            self._led(255, 0, 0)
            self._move(lin_y=0.4, duration=0.25)
            self._beat()

            # right hit
            self._led(0, 0, 255)
            self._move(lin_y=-0.4, duration=0.25)
            self._beat()

            # forward bounce
            self._led(0, 255, 0)
            self._move(lin_x=0.35, duration=0.2)
            self._move(lin_x=-0.35, duration=0.2)

            # spin accent
            self._move(ang_z=2.0, duration=0.3)
            self._beat()

        # =========================
        # 🔥 HEAD (camera groove)
        # =========================
        for _ in range(6):
            self._servo(2, 1300)
            self._servo(1, 1300)
            self._beep(2200, 0.05)

            time.sleep(0.1)

            self._servo(2, 1700)
            self._servo(1, 1700)
            self._beep(1800, 0.05)

            time.sleep(0.1)

        # =========================
        # 🔥 FAST SPIN DROP
        # =========================
        self._led(255, 255, 0)

        for _ in range(3):
            self._move(ang_z=3.0, duration=0.4)
            self._beep(2600, 0.05)

        # =========================
        # 🔥 FINALE (signature move)
        # =========================
        for _ in range(3):
            self._move(lin_y=0.5, duration=0.2)
            self._move(lin_y=-0.5, duration=0.2)
            self._beep(2000, 0.05)

        self._led(255, 255, 255)

        # final pose
        self._servo(1, 1500)
        self._servo(2, 1500)

        self.cmd_pub.publish(Twist())
