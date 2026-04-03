from ros_robot_controller_msgs.msg import SetPWMServoState, PWMServoState
import time

class Head:

    def __init__(self, pub):
        self.pub = pub

    def move(self, servo_id, pos, wait=0.5):
        msg = SetPWMServoState()
        msg.duration = 0.3

        s = PWMServoState()
        s.id = [servo_id]
        s.position = [pos]

        msg.state = [s]
        self.pub.publish(msg)

        time.sleep(wait)

