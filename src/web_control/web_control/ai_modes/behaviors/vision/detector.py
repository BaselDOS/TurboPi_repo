from ultralytics import YOLO
import cv2


class Detector:

    def __init__(self):
        self.model = YOLO("yolo26n.pt")
        self.target = "sports ball"

    def detect(self, frame):

        if frame is None:
            return [], False

        h, w = frame.shape[:2]

        # keep your crop logic, but make inference lighter
        x0 = int(w * 0.2)
        x1 = int(w * 0.8)
        y0 = int(h * 0.2)
        y1 = int(h * 0.9)

        crop = frame[y0:y1, x0:x1]

        if crop.size == 0:
            return [], False

        results = self.model(
            crop,
            imgsz=256,     # lighter than 352
            conf=0.15,
            iou=0.4,
            verbose=False
        )

        boxes = []
        found = False

        for r in results:
            for b in r.boxes:
                x1b, y1b, x2b, y2b = map(int, b.xyxy[0])
                cls = int(b.cls[0])
                label = self.model.names[cls]

                # map crop coords back to full frame
                x1b += x0
                x2b += x0
                y1b += y0
                y2b += y0

                boxes.append((x1b, y1b, x2b, y2b, label))

                if label == self.target:
                    found = True

        return boxes, found
