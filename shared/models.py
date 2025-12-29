from sqlalchemy import Column, Integer, String, JSON, DateTime, Float
from sqlalchemy.sql import func
from shared.database import Base

class DetectionResult(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, index=True)
    frame_path = Column(String)
    frame_index = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Store list of detections: [{class: "person", conf: 0.9, box: [x1, y1, x2, y2]}, ...]
    detections = Column(JSON) 
