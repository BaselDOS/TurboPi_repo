import rclpy
import cv2
import time

from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from cv_bridge import CvBridge

from .vision_detector import VisionDetector
from .optical_flow import OpticalFlowDetector
from .motion_controller import MotionController


class AvoidanceNode(Node):

    def __init__(self):
        super().__init__('avoidance_node')

        self.bridge = CvBridge()
        self.distance = 999.0

        self.vision = VisionDetector()
        self.flow = OpticalFlowDetector()
        self.motion = MotionController()

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.debug_pub = self.create_publisher(
            Image,
            '/avoidance/debug_image',
            10
        )

        self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10
        )

        self.create_subscription(
            Int32,
            '/sonar_controller/get_distance',
            self.distance_callback,
            10
        )

        self.get_logger().info("Avoidance node started")

    # -----------------------------
    def distance_callback(self, msg):
        try:
            self.distance = msg.data / 10.0
        except Exception:
            self.distance = 999.0

    # -----------------------------
    def publish_cmd(self, x, y, z):
        msg = Twist()
        msg.linear.x = float(x)
        msg.linear.y = float(y)
        msg.angular.z = float(z)
        self.cmd_pub.publish(msg)

    # -----------------------------
    def stop_robot(self):
        """🔥 HARD STOP (VERY IMPORTANT)"""
        msg = Twist()

        # publish multiple times to guarantee stop
        for _ in range(5):
            self.cmd_pub.publish(msg)
            time.sleep(0.05)

        self.get_logger().info("Robot STOPPED")

    # -----------------------------
    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().warn(f"Image conversion failed: {e}")
            return

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow_val = self.flow.compute(gray)

            left, center, right = self.vision.detect(frame)

            x, y, z = self.motion.decide(
                left,
                center,
                right,
                flow_val,
                self.distance
            )

            # DEBUG TEXT
            cv2.putText(
                frame,
                f"DIST: {self.distance:.1f} cm",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"FLOW: {flow_val:.3f}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

            # MOVE
            self.publish_cmd(x, y, z)

            # DEBUG STREAM
            debug_msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")
            self.debug_pub.publish(debug_msg)

        except Exception as e:
            self.get_logger().warn(f"Avoidance processing failed: {e}")


# ==============================
def main(args=None):
    rclpy.init(args=args)

    node = AvoidanceNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        # 🔥 CRITICAL FIX
        node.stop_robot()

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
