import cv2
import logging
from typing import List
from storage import VideoStorage

logger = logging.getLogger(__name__)

def extract_frames(video_path: str, video_id: str, storage: VideoStorage, sample_rate_sec: int = 1) -> List[str]:
    """
    Extracts frames from a video file and saves them to storage.
    
    Args:
        video_path: Local path to the video file.
        video_id: Unique identifier for the video.
        storage: Storage interface implementation.
        sample_rate_sec: Extract 1 frame every X seconds. Default 1.
        
    Returns:
        List of paths to the saved frames.
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30 # Fallback
        
    frame_interval = int(fps * sample_rate_sec)
    frame_count = 0
    saved_frames = []
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        if frame_count % frame_interval == 0:
            # Encode frame to JPEG bytes
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                frame_idx = frame_count
                frame_path = storage.save_frame(video_id, frame_idx, buffer.tobytes())
                saved_frames.append(frame_path)
                
        frame_count += 1
        
    cap.release()
    logger.info(f"Extracted {len(saved_frames)} frames from video {video_id}")
    return saved_frames
