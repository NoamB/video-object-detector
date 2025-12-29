from pydantic import BaseModel, Field
from typing import List, Optional

class VideoTask(BaseModel):
    """Schema for video upload tasks."""
    video_id: str
    video_path: str

class FrameTask(BaseModel):
    """Schema for individual frame extraction tasks."""
    video_id: str
    frame_path: str
    frame_index: int
    frame_hash: str
    video_hash: str

class DetectionSchema(BaseModel):
    """Schema for a single object detection result."""
    class_name: str = Field(..., alias="class")
    confidence: float = Field(..., alias="conf")
    bbox: List[float] # [x1, y1, x2, y2]

    class Config:
        populate_by_name = True

class DetectionResultBatch(BaseModel):
    """Schema for a batch of detections for a specific frame."""
    video_id: str
    frame_path: str
    frame_index: int
    detections: List[DetectionSchema]
