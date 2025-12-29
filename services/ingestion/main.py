from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Dict
import uuid
import logging
from shared.storage import FileSystemStorage
from shared.mq import KafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Ingestion Service")

# Initialize Singletons
storage = FileSystemStorage()
# Topic for initial video uploads
producer = KafkaProducer(topic="video-uploads")

@app.on_event("startup")
async def startup_event():
    await producer.start()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

@app.post("/upload")
async def upload_video(
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
        # 1. Save video first
        video_path = await storage.save_video(file, video_id)
        
        # 2. Publish Task to Kafka
        # This confirms the message is in the buffer before returning to user
        await producer.publish({
            "video_id": video_id,
            "video_path": video_path
        })
        
        logger.info(f"Video {video_id} saved and published to 'video-uploads'")
        
        return {
            "video_id": video_id, 
            "status": "published",
            "message": "Video received and queued for processing"
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
