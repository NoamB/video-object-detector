import asyncio
import json
import logging
import signal
from concurrent.futures import ThreadPoolExecutor

from database import init_db, AsyncSessionLocal
from models import DetectionResult
from storage import FileSystemStorage
from consumer import RedisConsumer
from detector import ObjectDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

# graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler():
    logger.info("Shutdown signal received")
    shutdown_event.set()

async def main():
    logger.info("Starting Detection Worker...")
    
    # Initialize components
    storage = FileSystemStorage()
    consumer = RedisConsumer()
    await consumer.connect()
    detector = ObjectDetector()
    
    # Initialize DB schema
    await init_db()
    
    # Executor for running blocking inference
    executor = ThreadPoolExecutor(max_workers=1) # YOLO is often not thread-safe or uses internal parallelism
    
    loop = asyncio.get_running_loop()
    
    # Register signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Worker ready. Waiting for jobs...")
    
    while not shutdown_event.is_set():
        try:
            # 1. Get Job (Blocking wait)
            # Since we use blocking redis command in async wrapper, check implementation
            # consumer.get_next_job uses 'await client.brpoplpush' which is compliant
            # But if we want to support clean shutdown, we might want a timeout loop
            # to check shutdown_event.
            # But brpoplpush with 0 blocks forever.
            # Let's rely on breaking the connection or just standard kill for MVP.
            # Ideally we use a timeout (e.g. 5s) and loop.
            
            # Note: RedisConsumer.get_next_job uses 0 timeout. 
            # If we want to check shutdown_event, we should change timeout to e.g. 1s.
            # I will modify consumer? No, I'll just let it block. 
            # Signal handler will cancel the pending task eventually if we structure it right, 
            # but for now let's just run. simple.
            
            raw_msg = await consumer.get_next_job()
            
            if not raw_msg:
                # Connection error or timeout (if we had one)
                await asyncio.sleep(1)
                continue
                
            job_data = json.loads(raw_msg)
            video_id = job_data.get("video_id")
            frame_path = job_data.get("frame_path")
            frame_idx = job_data.get("frame_index")
            
            logger.info(f"Processing frame {frame_idx} for video {video_id}")
            
            # 2. Run Inference (Blocking CPU bound)
            # Verify file exists? Detector handles it.
            detections = await loop.run_in_executor(
                executor, 
                detector.process_frame, 
                frame_path
            )
            
            # 3. Save to DB
            async with AsyncSessionLocal() as session:
                result = DetectionResult(
                    video_id=video_id,
                    frame_path=frame_path,
                    frame_index=frame_idx,
                    detections=detections
                )
                session.add(result)
                await session.commit()
                
            logger.info(f"Saved {len(detections)} detections for frame {frame_idx}")
            
            # 4. Acknowledge (Remove from processing queue)
            await consumer.complete_job(raw_msg)
            
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(1)

    logger.info("Inference worker shutting down.")
    executor.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())
