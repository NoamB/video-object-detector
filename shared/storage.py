import os
import shutil
import hashlib
from typing import Protocol, Any

# Define UploadFile type loosely to avoid hard dependency on FastAPI in shared?
# Or we just assume shared env has FastAPI installed (or at least types).
# But Detection Service might not need FastAPI.
# Let's use Any or Protocol for the file object to avoid import error if FastAPI is missing in Worker.
class UploadFileProtocol(Protocol):
    file: Any
    filename: str

class VideoStorage(Protocol):
    """
    Abstract interface for video and frame storage.
    """
    async def save_video(self, file: UploadFileProtocol, video_id: str) -> str:
        """Save an uploaded video file."""
        ...

    def save_frame(self, video_id: str, frame_id: int, frame_data: bytes) -> str:
        """Save a single frame image."""
        ...
        
    def delete_video(self, video_path: str) -> None:
        """Delete the source video."""
        ...

    def get_frame_path(self, frame_reference: str) -> str:
        """Resolves the read path for a frame reference."""
        ...

class FileSystemStorage:
    """
    Implementation of VideoStorage using a local filesystem.
    """
    def __init__(self, base_path: str = "/data"):
        self.base_path = base_path
        self.frames_path = os.path.join(base_path, "frames")
        self.videos_path = os.path.join(base_path, "videos")
        
        # Ensure base directories exist (safe to call even if read-only mount, though usually it's rw)
        os.makedirs(self.frames_path, exist_ok=True)
        os.makedirs(self.videos_path, exist_ok=True)

    async def save_video(self, file: UploadFileProtocol, video_id: str) -> str:
        file_path = os.path.join(self.videos_path, f"{video_id}.mp4")
        
        # Stream the file to disk
        # 'file.file' is a python file-like object
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

    def get_frame_path(self, frame_reference: str) -> str:
        # In FileSystemStorage, the reference IS the path
        return frame_reference

    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Computes SHA256 hash of byte data."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Computes SHA256 hash of a file in chunks."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
