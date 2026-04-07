#!/usr/bin/env python3
import threading
import rclpy
import time
from rclpy.node import Node
from sensor_msgs.msg import Image


class InternalStreamBridge(Node):

    def __init__(self):
        super().__init__('internal_stream_bridge')

        self.last_msg = None
        self.lock = threading.Lock()

        self.sub = self.create_subscription(
            Image,
            '/image_raw',
            self._callback,
            10
        )

        self.pub = self.create_publisher(
            Image,
            '/image_debug',
            10
        )

        # 🔥 ACTIVE publisher loop (20Hz)
        self.thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.thread.start()

        self.get_logger().info("Internal Stream Bridge started")

    def _callback(self, msg):
        with self.lock:
            self.last_msg = msg

    def _publish_loop(self):
        rate = 0.05  # 20Hz

        while rclpy.ok():
            msg = None

            with self.lock:
                msg = self.last_msg

            if msg is not None:
                self.pub.publish(msg)

            time.sleep(rate)


def start_stream_bridge():
    def run():
        try:
            rclpy.init(args=None)
            node = InternalStreamBridge()
            rclpy.spin(node)
        except Exception as e:
            print("Stream bridge error:", e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
