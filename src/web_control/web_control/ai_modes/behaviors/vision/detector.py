from ultralytics import YOLO

class Detector:

    def __init__(self):
        self.model = YOLO("yolo26n.pt")

    def detect(self, frame):

        h, w = frame.shape[:2]

        # center crop
        y1_crop = int(h * 0.2)
        y2_crop = int(h * 0.9)
        x1_crop = int(w * 0.2)
        x2_crop = int(w * 0.8)

        crop = frame[y1_crop:y2_crop, x1_crop:x2_crop]

        results = self.model(
            crop,
            imgsz=352,      # ✅ optimized
            conf=0.15,
            iou=0.4,
            verbose=False
        )

        boxes = []

        for r in results:
            for b in r.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0])
                conf = float(b.conf[0])
                cls = int(b.cls[0])
                label = self.model.names[cls]

                # remap to original frame
                x1 += x1_crop
                x2 += x1_crop
                y1 += y1_crop
                y2 += y1_crop

                boxes.append((x1, y1, x2, y2, label, conf))

        return boxes
