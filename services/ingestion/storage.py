import os
import shutil
from typing import Protocol
from fastapi import UploadFile

class VideoStorage(Protocol):
    """
    Abstract interface for video and frame storage.
    """
    async def save_video(self, file: UploadFile, video_id: str) -> str:
        """
        Save an uploaded video file.
        Returns the absolute path to the saved file.
        """
        ...

    def save_frame(self, video_id: str, frame_id: int, frame_data: bytes) -> str:
        """
        Save a single frame image.
        Returns the absolute path (or partial reference) to the saved frame.
        """
        ...
        
    def delete_video(self, video_path: str) -> None:
        """
        Delete the source video after processing.
        """
        ...

class FileSystemStorage:
    """
    Implementation of VideoStorage using a local filesystem (Docker Volume).
    """
    def __init__(self, base_path: str = "/data"):
        self.base_path = base_path
        self.frames_path = os.path.join(base_path, "frames")
        self.videos_path = os.path.join(base_path, "videos")
        
        # Ensure base directories exist
        os.makedirs(self.frames_path, exist_ok=True)
        os.makedirs(self.videos_path, exist_ok=True)

    async def save_video(self, file: UploadFile, video_id: str) -> str:
        file_path = os.path.join(self.videos_path, f"{video_id}.mp4")
        
        # Stream the file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return file_path

    def save_frame(self, video_id: str, frame_id: int, frame_data: bytes) -> str:
        # Create directory for this video's frames if not exists
        video_frame_dir = os.path.join(self.frames_path, video_id)
        os.makedirs(video_frame_dir, exist_ok=True)
        
        frame_path = os.path.join(video_frame_dir, f"{frame_id}.jpg")
        
        with open(frame_path, "wb") as f:
            f.write(frame_data)
            
        return frame_path

    def delete_video(self, video_path: str) -> None:
        if os.path.exists(video_path):
            os.remove(video_path)
