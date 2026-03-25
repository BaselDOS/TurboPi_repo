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
    def _move(self, lin_x=0.0, lin_y=0.0, ang_z=0.0, duration=1.0):
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
        msg.duration = 0.2
        self.servo_pub.publish(msg)

    # =========================
    def _beep(self):
        msg = BuzzerState()
        msg.freq = 2000
        msg.on_time = 0.2
        msg.off_time = 0.01
        msg.repeat = 1
        self.buzzer_pub.publish(msg)

    # =========================
    def fun_dance(self):

        # 1. LED flash
        self._led(255, 0, 0)
        time.sleep(0.2)
        self._led(0, 255, 0)
        time.sleep(0.2)
        self._led(0, 0, 255)

        # 2. spin
        self._move(ang_z=1.5, duration=1.5)

        # 3. forward + backward
        self._move(lin_x=0.3, duration=1)
        self._move(lin_x=-0.3, duration=1)

        # 4. camera dance
        for _ in range(3):
            self._servo(1, 1300)
            time.sleep(0.2)
            self._servo(1, 1700)
            time.sleep(0.2)

        # 5. beep rhythm
        for _ in range(3):
            self._beep()
            time.sleep(0.3)

        # 6. finish pose
        self._led(255, 255, 0)
