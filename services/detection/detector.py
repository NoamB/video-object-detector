from ultralytics import YOLO
import cv2
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ObjectDetector:
    def __init__(self, model_name: str = "yolov8n.pt"):
        # "n" is nano model (fastest, less accurate). Good for MVP.
        logger.info(f"Loading YOLO model: {model_name}")
        self.model = YOLO(model_name)

    def process_frame(self, frame_path: str) -> List[Dict[str, Any]]:
        """
        Run inference on a single frame.
        Returns a list of detections.
        """
        img = cv2.imread(frame_path)
        if img is None:
            logger.warning(f"Could not read image at {frame_path}")
            return []
            
        results = self.model(img, verbose=False) # Disable printing to stdout
        detections = []
        
        for result in results:
            for box in result.boxes:
                detections.append({
                    "class": self.model.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": box.xyxyn.cpu().numpy().tolist()[0] # [x1, y1, x2, y2]
                })
                
        return detections
