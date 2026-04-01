import cv2
import numpy as np

class StuckDetector:

    def __init__(self):
        self.prev = None

    def is_stuck(self, frame):

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.prev is None:
            self.prev = gray
            return False

        diff = cv2.absdiff(self.prev, gray)
        score = np.mean(diff)

        self.prev = gray

        return score < 0.5
