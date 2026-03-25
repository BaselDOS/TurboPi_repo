import time

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from std_msgs.msg import UInt16

from .robot_controller import RobotController
from .web_server import WebServer


class WebControlNode(Node):

    def __init__(self):
        super().__init__('web_control_node')

        pkg_share = get_package_share_directory('web_control')

        self.robot = RobotController(self)
        self.web = WebServer(self, pkg_share)
        self.bridge = CvBridge()

        self.camera_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.camera_callback,
            10
        )

        self.battery_sub = self.create_subscription(
            UInt16,
            '/ros_robot_controller/battery',
            self.battery_callback,
            10
        )

        self.avoidance_sub = self.create_subscription(
            Image,
            '/avoidance/debug_image',
            self.avoidance_callback,
            10
        )

        self.create_timer(0.5, self.health_timer)

        self.get_logger().info("UI server started")

    def camera_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            with self.web.frame_lock:
                self.web.raw_frame = frame

            self.web.last_camera_time = time.time()
            self.web.camera_ok = True

        except Exception as e:
            self.get_logger().warn(f"Camera callback error: {e}")

    def battery_callback(self, msg):
        try:
            self.web.battery_voltage = msg.data / 1000.0
            self.web.last_battery_time = time.time()
        except Exception as e:
            self.get_logger().warn(f"Battery callback error: {e}")

    def avoidance_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            with self.web.frame_lock:
                self.web.debug_frame = frame

        except Exception as e:
            self.get_logger().warn(f"Avoidance debug callback error: {e}")

    def health_timer(self):
        now = time.time()

        if now - self.web.last_camera_time > 2.5:
            self.web.camera_ok = False

        if now - self.web.last_battery_time > 5.0:
            self.web.battery_voltage = None


def main(args=None):
    rclpy.init(args=args)

    node = WebControlNode()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
