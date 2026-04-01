import cv2
import numpy as np

class OpticalFlowDetector:

    def __init__(self):
        self.prev_gray = None

    def compute(self, gray):

        if self.prev_gray is None:
            self.prev_gray = gray
            return 1.0

        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            gray,
            None,
            0.5,
            3,
            15,
            3,
            5,
            1.2,
            0
        )

        mag, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
        avg_flow = np.mean(mag)

        self.prev_gray = gray

        return avg_flow
