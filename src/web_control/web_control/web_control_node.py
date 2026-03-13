import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from std_msgs.msg import Float32MultiArray

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from std_msgs.msg import UInt16
from .robot_controller import RobotController
from .web_server import WebServer


class WebControlNode(Node):

    def __init__(self):
        super().__init__('web_control_node')

        pkg_share = get_package_share_directory('web_control')

        # Robot control
        self.robot = RobotController(self)

        # Web server
        self.web = WebServer(self, pkg_share)

        self.bridge = CvBridge()

        # Camera subscriber
        self.camera_sub = self.create_subscription(
            Image,
            '/image_raw',   # change this if your real topic is different
            self.camera_callback,
            10
        )

        # Battery subscriber
        self.battery_sub = self.create_subscription(
            UInt16,
            '/ros_robot_controller/battery',    # change this if your real topic is different
            self.battery_callback,
            10
        )

        self.get_logger().info("UI server started")

    def camera_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            with self.web.frame_lock:
                self.web.frame = frame

            self.web.camera_ok = True
        except Exception:
            self.web.camera_ok = False

    def battery_callback(self, msg):
        try:
            self.web.battery_voltage = msg.data/1000.0
        except Exception:
            self.web.battery_voltage = None


def main(args=None):
    rclpy.init(args=args)

    node = WebControlNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()
