import cv2

class TargetFollow:

    def __init__(self):
        self.center_tolerance = 40

        # servo limits
        self.servo_min = 1200
        self.servo_max = 1800
        self.servo_center = 1500

    def compute(self, frame, boxes):

        target_box = None
        max_area = 0

        # find biggest sports ball
        for (x1, y1, x2, y2, label) in boxes:
            if label == "sports ball":
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    target_box = (x1, y1, x2, y2)

        if target_box is None:
            return None

        x1, y1, x2, y2 = target_box

        h, w = frame.shape[:2]
        cx = (x1 + x2) // 2

        error = cx - (w // 2)

        # ===== ABSOLUTE CONTROL (NO DRIFT) =====
        gain = 0.5  # tune this

        new_pos = int(self.servo_center - error * gain)

        # clamp
        new_pos = max(self.servo_min, min(self.servo_max, new_pos))

        return new_pos
