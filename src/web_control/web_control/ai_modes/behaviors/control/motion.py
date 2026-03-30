from geometry_msgs.msg import Twist
import time

class Motion:

    def __init__(self, pub):
        self.pub = pub

    def _send(self, lin=0.0, ang=0.0):
        msg = Twist()
        msg.linear.x = lin
        msg.angular.z = ang
        self.pub.publish(msg)

    def stop(self):
        for _ in range(5):
            self._send()
            time.sleep(0.05)

    def forward(self, t=1.5):
        end = time.time() + t
        while time.time() < end:
            self._send(0.3, 0.0)
            time.sleep(0.05)

    def rotate_left(self, t=1.0):
        end = time.time() + t
        while time.time() < end:
            self._send(0.0, 1.2)
            time.sleep(0.05)

    def rotate_right(self, t=1.0):
        end = time.time() + t
        while time.time() < end:
            self._send(0.0, -1.2)
            time.sleep(0.05)
