from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from typing import Dict
import uuid
import os
import logging
from shared.storage import FileSystemStorage
from shared.mq import KafkaProducer
from processing import extract_frames

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Ingestion Service")

# Initialize Singletons
storage = FileSystemStorage()
producer = KafkaProducer()

@app.on_event("startup")
async def startup_event():
    await producer.start()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

async def process_video_bg(video_path: str, video_id: str):
    """
    Background task to extract frames and publish to Kafka.
    """
    try:
        logger.info(f"Starting processing for video {video_id}")
        
        # 1. Compute Video Hash
        video_hash = storage.compute_file_hash(video_path)
        logger.info(f"Video {video_id} hash: {video_hash}")
        
        # 2. Extract Frames
        frame_data = extract_frames(video_path, video_id, storage, sample_rate_sec=1)
        
        # 3. Publish to Kafka
        for path, frame_hash in frame_data:
            # Extract frame index from filename (e.g., "120.jpg" -> 120)
            filename = os.path.basename(path)
            try:
                frame_idx = int(os.path.splitext(filename)[0])
                await producer.publish_frame(
                    video_id, 
                    path, 
                    frame_idx, 
                    frame_hash=frame_hash,
                    video_hash=video_hash
                )
            except ValueError:
                logger.warning(f"Could not parse frame index from filename: {filename}")
                continue
                
        logger.info(f"Published {len(frame_data)} frames for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
    finally:
        # 3. Cleanup Source Video
        # We must eventually clean up to save space.
        logger.info(f"Cleaning up source video {video_path}")
        storage.delete_video(video_path)

@app.post("/upload", status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
) -> Dict[str, str]:
    """
    Upload a video file for processing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    video_id = str(uuid.uuid4())
    logger.info(f"Receiving upload: {file.filename} (ID: {video_id})")
    
    try:
        # Save video first (Async input I/O)
        video_path = await storage.save_video(file, video_id)
        
        # Offload CPU-bound extraction to background task
        background_tasks.add_task(process_video_bg, video_path, video_id)
        
        return {
            "video_id": video_id, 
            "status": "accepted",
            "message": "Video accepted for processing"
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
