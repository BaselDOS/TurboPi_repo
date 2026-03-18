from geometry_msgs.msg import Twist

class MovementExecutor:

    def __init__(self,node):

        self.node = node

        self.pub = node.create_publisher(
            Twist,
            "cmd_vel",
            10
        )

    def execute(self,cmd):

        twist = Twist()

        v = cmd["value"]

        if v == "forward":
            twist.linear.x = 0.3

        elif v == "back":
            twist.linear.x = -0.3

        elif v == "left":
            twist.linear.y = 0.3

        elif v == "right":
            twist.linear.y = -0.3

        elif v == "turn_left":
            twist.angular.z = 2.0

        elif v == "turn_right":
            twist.angular.z = -2.0

        elif v == "stop":
            twist = Twist()

        self.pub.publish(twist)
