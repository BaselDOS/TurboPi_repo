from geometry_msgs.msg import Twist
from ros_robot_controller_msgs.msg import SetPWMServoState, PWMServoState


class RobotController:

    def __init__(self, node):
        self.node = node
        
        self.manual_control = True

        self.move_x = 0.0
        self.move_y = 0.0
        self.rotate_dir = 0

        self.cam_pan = 0.0
        self.cam_tilt = 0.0

        self.servo_x = 1500
        self.servo_y = 1500

        self.cmd_vel_pub = node.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.servo_pub = node.create_publisher(
            SetPWMServoState,
            '/ros_robot_controller/pwm_servo/set_state',
            10
        )

        node.create_timer(0.05, self.movement_loop)
        node.create_timer(0.05, self.camera_loop)

    def movement_loop(self):
        if not self.manual_control:
            return
        twist = Twist()

        twist.linear.x = self.move_y * 0.6
        twist.linear.y = -self.move_x * 0.6

        if self.rotate_dir == 1:
            twist.angular.z = -8.0
        elif self.rotate_dir == -1:
            twist.angular.z = 8.0
        else:
            twist.angular.z = 0.0

        self.cmd_vel_pub.publish(twist)

    def camera_loop(self):
        step = 10

        self.servo_x += int(self.cam_pan * step)
        self.servo_y += int(self.cam_tilt * step)

        self.servo_x = max(800, min(2200, self.servo_x))
        self.servo_y = max(800, min(2200, self.servo_y))

        msg = SetPWMServoState()

        s1 = PWMServoState()
        s1.id = [1]
        s1.position = [self.servo_y]

        s2 = PWMServoState()
        s2.id = [2]
        s2.position = [self.servo_x]

        msg.state = [s1, s2]
        msg.duration = 0.05

        self.servo_pub.publish(msg)
