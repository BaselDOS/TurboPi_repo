import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from speech import speech
from ai_modes.core.config import *


class VisionExecutor(Node):
    def __init__(self):
        super().__init__("vision_executor")

        self.bridge = CvBridge()
        self.latest_frame = None

        self.subscription = self.create_subscription(
            Image,
            "/image_raw",
            self.image_callback,
            10
        )

        self.client = speech.OpenAIAPI(vllm_api_key, vllm_base_url)
        self.model = "qwen/qwen3.5-flash-02-23"

    def image_callback(self, msg):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding="bgr8"
            )
        except Exception as e:
            print("CV Bridge error:", e)

    def describe(self):
        if self.latest_frame is None:
            return "I don't see anything yet."

        print("Sending image to OpenRouter...")
        print("Model:", self.model)

        try:
            result = self.client.vllm(
                "",
                self.latest_frame,
                prompt="Describe what you see in the image",
                model=self.model
            )
            return result
        except Exception as e:
            print("Vision error:", e)
            return "Vision processing failed."
