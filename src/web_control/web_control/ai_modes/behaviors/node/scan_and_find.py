#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2
import threading
import time

from web_control.ai_modes.behaviors.vision.detector import Detector


class CleanYoloNode(Node):

    def __init__(self):
        super().__init__('clean_yolo_node')

        self.bridge = CvBridge()

        self.current_image = None
        self.running = True

        self.frame_count = 0
        self.process_every_n = 6

        self.last_boxes = []

        self.detector = Detector()

        self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            1
        )

        self.debug_pub = self.create_publisher(
            Image,
            '/avoidance/debug_image',
            1
        )

        threading.Thread(target=self.loop, daemon=True).start()

    def image_callback(self, msg):
        try:
            self.current_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except:
            pass

    def loop(self):

        while self.running:

            if self.current_image is None:
                time.sleep(0.02)
                continue

            frame = self.current_image

            self.frame_count += 1

            if self.frame_count % self.process_every_n == 0:
                try:
                    self.last_boxes = self.detector.detect(frame)
                except Exception as e:
                    self.get_logger().warn(f"YOLO error: {e}")

            for (x1, y1, x2, y2, label, conf) in self.last_boxes:

                color = (0,255,0)

                if label == "sports ball":
                    color = (0,0,255)

                cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
                cv2.putText(
                    frame,
                    f"{label} {conf:.2f}",
                    (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )

            cv2.putText(frame, "STREAM OK", (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

            cv2.putText(frame, f"Boxes: {len(self.last_boxes)}",
                        (20,80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

            try:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                self.debug_pub.publish(msg)
            except:
                pass

            time.sleep(0.03)


def main():
    rclpy.init()
    node = CleanYoloNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    finally:
        node.running = False
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
