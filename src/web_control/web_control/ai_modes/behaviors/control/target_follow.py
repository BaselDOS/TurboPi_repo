import cv2

class TargetFollow:

    def __init__(self):
        self.center_tolerance = 50   # dead-zone (tune 30–70)

        # servo limits
        self.servo_min = 1200
        self.servo_max = 1800
        self.servo_center = 1500

        # smoothing
        self.current_pos = 1500
        self.alpha = 0.25        # smoothing factor (0.15–0.4)
        self.max_step = 25       # max movement per update (15–40)

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

        center_x = w // 2
        error = cx - center_x

        # ===== DEAD ZONE =====
        if abs(error) < self.center_tolerance:
            return self.current_pos

        # ===== TARGET POSITION =====
        gain = 0.4
        target_pos = int(self.servo_center - error * gain)

        # clamp
        target_pos = max(self.servo_min, min(self.servo_max, target_pos))

        # ===== SMOOTHING =====
        smoothed = int(
            self.current_pos * (1 - self.alpha) +
            target_pos * self.alpha
        )

        # ===== SPEED LIMIT =====
        diff = smoothed - self.current_pos

        if abs(diff) > self.max_step:
            smoothed = self.current_pos + self.max_step * (1 if diff > 0 else -1)

        self.current_pos = smoothed

        return self.current_pos
