import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.future import select
import logging

# Add shared and detection service paths to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "detection")))

from detection.database import AsyncSessionLocal
from detection.models import DetectionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Analytics Dashboard")

# Serve frames as static files
# In docker, frames are at /data/frames
FRAME_STORAGE_PATH = os.getenv("FRAME_STORAGE_PATH", "/data/frames")
if os.path.exists(FRAME_STORAGE_PATH):
    app.mount("/frames", StaticFiles(directory=FRAME_STORAGE_PATH), name="frames")
else:
    logger.warning(f"Frame storage path {FRAME_STORAGE_PATH} does not exist.")

current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, "templates")
logger.info(f"Loading templates from: {template_dir}")
templates = Jinja2Templates(directory=template_dir)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
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
                "image_url": f"/frames/{os.path.basename(os.path.dirname(d.frame_path))}/{os.path.basename(d.frame_path)}"
            }
            for d in detections
        ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
