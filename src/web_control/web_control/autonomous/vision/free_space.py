import cv2

class FreeSpace:

    def analyze(self, frame):

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        h, w = edges.shape

        left = edges[:, :w//3]
        center = edges[:, w//3:2*w//3]
        right = edges[:, 2*w//3:]

        return {
            "left": cv2.countNonZero(left),
            "center": cv2.countNonZero(center),
            "right": cv2.countNonZero(right)
        }
