import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from std_msgs.msg import Float32

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
        
        self.bridge = CvBridge()
        
        #camera_sub
        self.camera_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.camera_callback,
            10
        )

        #battery_sub
        self.battery_sub = self.create_subscription(
            Float32,
            '/battery_voltage',
            self.battery_callback,
            10
        )

    def camera_callback(self, msg):

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        with self.server.frame_lock:
            self.server.frame = frame

        self.server.camera_ok = True

    def battery_callback(self, msg):
        self.server.battery_voltage = msg.data

def main(args=None):

    rclpy.init(args=args)

    node = WebControlNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()
