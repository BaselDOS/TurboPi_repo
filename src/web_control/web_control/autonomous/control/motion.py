from geometry_msgs.msg import Twist

class Motion:

    def __init__(self, pub):
        self.pub = pub

    def _send(self, lin=0.0, ang=0.0):
        msg = Twist()
        msg.linear.x = lin
        msg.angular.z = ang
        self.pub.publish(msg)

    def stop(self):
        self._send(0.0, 0.0)

    def forward(self):
        self._send(0.5, 0.0)

    def backward(self):
        self._send(-0.5,0.0)

    def rotate_left(self):
        self._send(0.0, 2.0)

    def rotate_right(self):
        self._send(0.0, -2.0)

