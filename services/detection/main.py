import asyncio
import json
import logging
import signal
from concurrent.futures import ThreadPoolExecutor

from database import init_db, AsyncSessionLocal
from models import DetectionResult
from shared.storage import FileSystemStorage
from shared.mq import RedisConsumer
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
            job_info = await consumer.get_next_job()
            
            if not job_info:
                await asyncio.sleep(1)
                continue
                
            msg_id, job_data = job_info
            video_id = job_data.get("video_id")
            frame_path = job_data.get("frame_path")
            frame_idx = int(job_data.get("frame_index"))
            expected_hash = job_data.get("frame_hash")
            
            logger.info(f"Processing frame {frame_idx} for video {video_id} (ID: {msg_id})")
            
            # --- Hash Verification ---
            if expected_hash:
                try:
                    with open(frame_path, "rb") as f:
                        actual_hash = storage.compute_hash(f.read())
                    if actual_hash != expected_hash:
                        logger.error(f"CORRUPTION DETECTED: Hash mismatch for frame {frame_idx} of video {video_id}. "
                                     f"Expected: {expected_hash}, Actual: {actual_hash}")
                        # Acknowledge to drop it so it's not retried indefinitely in PEL
                        await consumer.acknowledge(msg_id)
                        continue
                except Exception as e:
                    logger.error(f"Failed to read/verify hash for frame {frame_path}: {e}")
                    await asyncio.sleep(1)
                    continue
            # --------------------------
            
            # 2. Run Inference (Blocking CPU bound)
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
            
            # 4. Acknowledge (XACK)
            await consumer.acknowledge(msg_id)
            
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(1)

    logger.info("Inference worker shutting down.")
    executor.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())
