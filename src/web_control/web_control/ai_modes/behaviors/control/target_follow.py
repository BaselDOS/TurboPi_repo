import cv2

class TargetFollow:

    def __init__(self):
        self.center_tolerance = 40

        # servo limits (tune if needed)
        self.servo_min = 1200
        self.servo_max = 1800
        self.servo_center = 1500

        self.current_pos = self.servo_center
        self.step = 30  # how fast the head moves

    def compute(self, frame, boxes):

        target_box = None
        max_area = 0

        # ===== find biggest sports ball =====
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

        error_x = cx - (w // 2)

        # ===== HEAD CONTROL =====
        if abs(error_x) < self.center_tolerance:
            return self.current_pos  # no movement

        if error_x > 0:
            # target is RIGHT → move head RIGHT
            self.current_pos -= self.step
        else:
            # target is LEFT → move head LEFT
            self.current_pos += self.step

        # clamp
        self.current_pos = max(self.servo_min, min(self.servo_max, self.current_pos))

        return self.current_pos
