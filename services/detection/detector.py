from ultralytics import YOLO
import cv2
import logging
from typing import List, Dict, Any
from shared.schemas import DetectionSchema

logger = logging.getLogger(__name__)

class ObjectDetector:
    def __init__(self, model_name: str = "yolov8n.pt") -> None:
        # "n" is nano model (fastest, less accurate). Good for MVP.
        logger.info(f"Loading YOLO model: {model_name}")
        self.model: YOLO = YOLO(model_name)

    def process_frame(self, frame_path: str) -> List[DetectionSchema]:
        """
        Run inference on a single frame.
        Returns a list of detections.
        """
        img: Any = cv2.imread(frame_path)
        if img is None:
            logger.warning(f"Could not read image at {frame_path}")
            return []
            
        results: Any = self.model(img, verbose=False) # Disable printing to stdout
        detections: List[DetectionSchema] = []
        
        for result in results:
            for box in result.boxes:
                cls_name: str = self.model.names[int(box.cls)]
                conf: float = float(box.conf)
                bbox: List[float] = box.xyxyn.cpu().numpy().tolist()[0] # [x1, y1, x2, y2]
                
                detections.append(DetectionSchema(
                    class_name=cls_name,
                    confidence=conf,
                    bbox=bbox
                ))
                
        return detections
