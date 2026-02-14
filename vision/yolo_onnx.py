import os
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np


@dataclass
class Detection:
    class_id: int
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0, inter_x2 - inter_x1)
    ih = max(0, inter_y2 - inter_y1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def _nms(boxes: List[List[int]], scores: List[float], iou_threshold: float) -> List[int]:
    idxs = list(range(len(boxes)))
    idxs.sort(key=lambda i: scores[i], reverse=True)
    keep: List[int] = []
    while idxs:
        i = idxs.pop(0)
        keep.append(i)
        idxs = [j for j in idxs if _iou(boxes[i], boxes[j]) < iou_threshold]
    return keep


class YoloOnnxDetector:
    def __init__(
        self,
        model_path: str,
        class_names: List[str],
        input_size: int = 320,
        conf_threshold: float = 0.4,
        iou_threshold: float = 0.45,
    ):
        self.model_path = model_path
        self.class_names = class_names
        self.input_size = int(input_size)
        self.conf_threshold = float(conf_threshold)
        self.iou_threshold = float(iou_threshold)
        self.net = None

        if os.path.exists(self.model_path):
            self.net = cv2.dnn.readNetFromONNX(self.model_path)

    def is_ready(self) -> bool:
        return self.net is not None

    def detect(self, frame_bgr) -> Optional[List[Detection]]:
        if self.net is None or frame_bgr is None:
            return None

        h, w = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame_bgr,
            scalefactor=1.0 / 255.0,
            size=(self.input_size, self.input_size),
            swapRB=True,
            crop=False,
        )
        self.net.setInput(blob)
        out = self.net.forward()

        preds = out
        if isinstance(preds, (list, tuple)):
            preds = preds[0]

        preds = np.squeeze(preds)
        if preds.ndim == 3:
            preds = np.squeeze(preds, axis=0)

        if preds.ndim != 2:
            return []

        feature_dim, box_dim = preds.shape
        if feature_dim < box_dim:
            data = preds.T
        else:
            data = preds

        num_cols = data.shape[1]
        if num_cols < 6:
            return []

        class_count = max(1, len(self.class_names))
        has_objectness = (num_cols - 5) == class_count

        boxes: List[List[int]] = []
        scores: List[float] = []
        class_ids: List[int] = []

        for row in data:
            x, y, bw, bh = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            if num_cols == 6:
                conf = float(row[4])
                cls = int(row[5])
            else:
                if has_objectness:
                    obj = float(row[4])
                    cls_scores = row[5:]
                    cls = int(np.argmax(cls_scores))
                    conf = obj * float(cls_scores[cls])
                else:
                    cls_scores = row[4:]
                    cls = int(np.argmax(cls_scores))
                    conf = float(cls_scores[cls])

            if conf > 1.0 and conf <= 100.0:
                conf = conf / 100.0

            if conf < self.conf_threshold:
                continue

            max_box_val = max(abs(x), abs(y), abs(bw), abs(bh))
            if max_box_val <= 1.5:
                cx = x * w
                cy = y * h
                ww = bw * w
                hh = bh * h
            elif max_box_val <= self.input_size * 1.5:
                cx = x * (w / self.input_size)
                cy = y * (h / self.input_size)
                ww = bw * (w / self.input_size)
                hh = bh * (h / self.input_size)
            else:
                cx, cy, ww, hh = x, y, bw, bh

            x1 = int(cx - ww / 2)
            y1 = int(cy - hh / 2)
            x2 = int(cx + ww / 2)
            y2 = int(cy + hh / 2)

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))

            if x2 <= x1 or y2 <= y1:
                continue

            boxes.append([x1, y1, x2, y2])
            scores.append(conf)
            class_ids.append(cls)

        if not boxes:
            return []

        keep = _nms(boxes, scores, self.iou_threshold)
        detections: List[Detection] = []
        for i in keep:
            cls = class_ids[i]
            label = self.class_names[cls] if 0 <= cls < len(self.class_names) else str(cls)
            x1, y1, x2, y2 = boxes[i]
            detections.append(
                Detection(class_id=int(cls), label=label, confidence=float(scores[i]), x1=x1, y1=y1, x2=x2, y2=y2)
            )
        return detections

    def draw(self, frame_bgr, detections: List[Detection]):
        if frame_bgr is None or not detections:
            return frame_bgr
        for det in detections:
            color = (0, 0, 255) if det.label.lower() == "fire" else (255, 128, 0)
            cv2.rectangle(frame_bgr, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            text = f"{det.label} {det.confidence:.2f}"
            cv2.putText(
                frame_bgr,
                text,
                (det.x1, max(0, det.y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )
        return frame_bgr
