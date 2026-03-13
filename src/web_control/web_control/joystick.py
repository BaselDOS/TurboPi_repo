import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray


class JoystickNode(Node):

    def __init__(self):
        super().__init__('joystick_mode')

        self.move_x = 0.0
        self.move_y = 0.0

        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.sub = self.create_subscription(
            Float32MultiArray,
            '/joystick_cmd',
            self.joy_callback,
            10
        )

        self.create_timer(0.05, self.loop)

    def joy_callback(self, msg):
        self.move_x = msg.data[0]
        self.move_y = msg.data[1]

    def loop(self):
        twist = Twist()

        twist.linear.x = self.move_y * 0.6
        twist.linear.y = -self.move_x * 0.6

        self.cmd_vel_pub.publish(twist)


def main():
    rclpy.init()

    node = JoystickNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
