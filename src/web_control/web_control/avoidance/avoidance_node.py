import sys
import os
sys.path.append(os.path.dirname(__file__))

import rclpy
import cv2

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

        self.distance = 999

        self.vision = VisionDetector()
        self.flow = OpticalFlowDetector()
        self.motion = MotionController()

        self.cmd_pub = self.create_publisher(Twist,'/cmd_vel',10)

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


    def distance_callback(self,msg):

        self.distance = msg.data / 10.0


    def publish_cmd(self,x,y,z):

        msg = Twist()

        msg.linear.x = float(x)
        msg.linear.y = float(y)
        msg.angular.z = float(z)

        self.cmd_pub.publish(msg)


    def image_callback(self,msg):

        frame = self.bridge.imgmsg_to_cv2(msg,"bgr8")

        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

        flow_val = self.flow.compute(gray)

        left,center,right = self.vision.detect(frame)

        x,y,z = self.motion.decide(
            left,
            center,
            right,
            flow_val,
            self.distance
        )

        self.publish_cmd(x,y,z)

        cv2.imshow("TurboPi Avoidance",frame)
        cv2.waitKey(1)


def main():

    rclpy.init()

    node = AvoidanceNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
