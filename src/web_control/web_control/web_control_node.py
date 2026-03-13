import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

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

        self.get_logger().info("UI server started")


def main(args=None):

    rclpy.init(args=args)

    node = WebControlNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()
