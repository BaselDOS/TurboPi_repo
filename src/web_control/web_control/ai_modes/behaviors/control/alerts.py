from ros_robot_controller_msgs.msg import BuzzerState
import time

class Alerts:

    def __init__(self, pub):
        self.pub = pub

    def beep5(self):
        for _ in range(5):
            msg = BuzzerState()
            msg.freq = 2000
            msg.on_time = 0.2
            msg.off_time = 0.1
            msg.repeat = 1
            self.pub.publish(msg)
            time.sleep(0.4)
