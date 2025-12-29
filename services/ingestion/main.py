from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List
import uuid
import logging
import os
from sqlalchemy.future import select

from shared.storage import FileSystemStorage
from shared.mq import KafkaProducer
from shared.database import init_db, AsyncSessionLocal
from shared.models import DetectionResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Ingestion & Analytics Service")

# Initialize Singletons
storage = FileSystemStorage()
# Topic for initial video uploads
producer = KafkaProducer(topic="video-uploads")

# Dashboard Setup
FRAME_STORAGE_PATH = os.getenv("FRAME_STORAGE_PATH", "/data/frames")
if os.path.exists(FRAME_STORAGE_PATH):
    app.mount("/frames", StaticFiles(directory=FRAME_STORAGE_PATH), name="frames")
else:
    logger.warning(f"Frame storage path {FRAME_STORAGE_PATH} does not exist.")

current_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

@app.on_event("startup")
async def startup_event():
    # 1. Start Kafka Producer
    await producer.start()
    # 2. Initialize Database
    logger.info("Initializing database...")
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

# --- Upload Endpoints ---

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

# --- Dashboard Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/results")
async def get_results():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DetectionResult).order_by(DetectionResult.timestamp.desc()).limit(100)
        )
        detections = result.scalars().all()
        
        return [
            {
                "id": d.id,
                "video_id": d.video_id,
                "frame_index": d.frame_index,
                "timestamp": d.timestamp.isoformat(),
                "detections": d.detections,
                # Convert absolute path to a URL path for the frontend
                # Expecting path like /data/frames/video_id/frame_idx.jpg
                "image_url": f"/frames/{os.path.basename(os.path.dirname(d.frame_path))}/{os.path.basename(d.frame_path)}"
            }
            for d in detections
        ]

@app.get("/health")
def health_check():
    return {"status": "ok"}
