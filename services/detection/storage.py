from typing import Protocol

class VideoStorage(Protocol):
    def get_frame_path(self, frame_reference: str) -> str:
        ...

class FileSystemStorage:
    """
    Storage implementation for local filesystem.
    In S3 version, this would download the file to a temp location.
    """
    def __init__(self, base_path: str = "/data"):
        self.base_path = base_path

    def get_frame_path(self, frame_reference: str) -> str:
        # For local filesystem, the reference in the message is already the absolute path.
        return frame_reference
