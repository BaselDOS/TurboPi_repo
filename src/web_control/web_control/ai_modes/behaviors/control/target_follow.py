import cv2

class TargetFollow:

    def __init__(self):
        self.center_tolerance = 60   # bigger = less jitter

        # servo limits
        self.servo_min = 1200
        self.servo_max = 1800
        self.servo_center = 1500

        # smoothing
        self.current_pos = 1500
        self.alpha = 0.25
        self.max_step = 25

        # distance control
        self.target_area = 9000

    def compute(self, frame, boxes):

        target_box = None
        max_area = 0

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

        # ===== HEAD =====
        if abs(error) < self.center_tolerance:
            target_pos = self.current_pos
        else:
            gain = 0.4
            target_pos = int(self.servo_center - error * gain)

        target_pos = max(self.servo_min, min(self.servo_max, target_pos))

        smoothed = int(
            self.current_pos * (1 - self.alpha) +
            target_pos * self.alpha
        )

        diff = smoothed - self.current_pos
        if abs(diff) > self.max_step:
            smoothed = self.current_pos + self.max_step * (1 if diff > 0 else -1)

        self.current_pos = smoothed

        # ===== ROTATION =====
        ang_z = 0.0
        if error > self.center_tolerance:
            ang_z = -0.5
        elif error < -self.center_tolerance:
            ang_z = 0.5

        # ===== DISTANCE =====
        lin_x = 0.0

        # ===== SAFE DISTANCE ZONE =====
        upper = self.target_area * 0.9
        lower = self.target_area * 0.5

        if max_area > upper:
            lin_x = -0.3  # too close → go back
        elif max_area < lower:
            lin_x = 0.3   # too far → go forward
        else:
            lin_x = 0.0    # good distance → stop 

        return self.current_pos, lin_x, ang_z
