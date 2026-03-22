import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from speech import speech
from core.config import *

class VisionExecutor(Node):

    def __init__(self):
        super().__init__('vision_executor')

        self.bridge = CvBridge()
        self.latest_frame = None

        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10
        )

        self.client = speech.OpenAIAPI(vllm_api_key, vllm_base_url)
        self.model = "openai/gpt-4o-mini"

    def image_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def describe(self):
        if self.latest_frame is None:
            return "I don't see anything yet."

        print("Sending ROS image to model...")

        result = self.client.vllm(
            "Describe what you see in the image",
            self.latest_frame,
            prompt='',
            model=self.model
        )

        return result
