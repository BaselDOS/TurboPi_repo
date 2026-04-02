import cv2


class TargetFollow:

    def __init__(self):
        # tuning params
        self.center_tolerance = 40
        self.kp_ang = 0.0025

        self.area_stop = 60000
        self.area_slow = 25000

    def compute(self, frame, boxes):

        target_box = None
        max_area = 0

        # ===== find biggest target =====
        for (x1, y1, x2, y2, label) in boxes:
            if label == "sports ball":
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    target_box = (x1, y1, x2, y2)

        if target_box is None:
            return None  # no target

        x1, y1, x2, y2 = target_box

        h, w = frame.shape[:2]
        cx = (x1 + x2) // 2

        error_x = cx - (w // 2)

        # ===== angular control =====
        if abs(error_x) > self.center_tolerance:
            ang_z = -self.kp_ang * error_x
        else:
            ang_z = 0.0

        # ===== forward control =====
        if max_area > self.area_stop:
            lin_x = 0.0
        elif max_area > self.area_slow:
            lin_x = 0.15
        else:
            lin_x = 0.30

        return float(lin_x), float(ang_z)
