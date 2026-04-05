import cv2
import numpy as np

class VisionDetector:

    def __init__(self):

        self.min_contour_area = 5000

        self.left_counter = 0
        self.center_counter = 0
        self.right_counter = 0


    def detect(self, frame):

        h, w = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray,(5,5),0)

        edges = cv2.Canny(blur,60,150)

        kernel = np.ones((5,5),np.uint8)
        edges = cv2.dilate(edges,kernel,iterations=1)

        contours,_ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        zone1 = w//3
        zone2 = 2*w//3

        left=False
        center=False
        right=False

        for c in contours:

            area = cv2.contourArea(c)

            if area < self.min_contour_area:
                continue

            x,y,bw,bh = cv2.boundingRect(c)

            cx = x + bw//2
            cy = y + bh//2

            if cy < h*0.45:
                continue

            if bh < 40:
                continue

            cv2.rectangle(frame,(x,y),(x+bw,y+bh),(0,255,0),2)

            if cx < zone1:
                left=True
            elif cx < zone2:
                center=True
            else:
                right=True

        self.left_counter = self.left_counter+1 if left else 0
        self.center_counter = self.center_counter+1 if center else 0
        self.right_counter = self.right_counter+1 if right else 0

        return (
            self.left_counter > 5,
            self.center_counter > 5,
            self.right_counter > 5
        )
