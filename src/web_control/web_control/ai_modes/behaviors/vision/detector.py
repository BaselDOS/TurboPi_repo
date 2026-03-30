from ultralytics import YOLO

class Detector:

    def __init__(self):
        self.model = YOLO("yolo26n.pt")
        self.target = "sports ball"

    def detect(self, frame):

        h, w = frame.shape[:2]

        crop = frame[int(h*0.2):int(h*0.9), int(w*0.2):int(w*0.8)]

        results = self.model(
            crop,
            imgsz=352,
            conf=0.15,
            iou=0.4,
            verbose=False
        )

        boxes = []
        found = False

        for r in results:
            for b in r.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0])
                cls = int(b.cls[0])
                label = self.model.names[cls]

                x1 += int(w*0.2)
                x2 += int(w*0.2)
                y1 += int(h*0.2)
                y2 += int(h*0.2)

                boxes.append((x1,y1,x2,y2,label))

                if label == self.target:
                    found = True

        return boxes, found
