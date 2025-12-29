import asyncio
import json
import logging
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from shared.database import init_db, AsyncSessionLocal
from shared.models import DetectionResult
from shared.storage import FileSystemStorage
from shared.mq import KafkaConsumer
from shared.schemas import FrameTask, DetectionSchema
from detector import ObjectDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger("worker")

# graceful shutdown
shutdown_event: asyncio.Event = asyncio.Event()

def signal_handler() -> None:
    logger.info("Shutdown signal received")
    shutdown_event.set()

async def main() -> None:
    logger.info("Starting Detection Worker...")
    
    # Auto-initialize DB tables
    await init_db()
    
    # Initialize components
    storage: FileSystemStorage = FileSystemStorage()
    consumer: KafkaConsumer = KafkaConsumer(topic="frame-tasks", group_id="detection-group")
    await consumer.start()
    detector: ObjectDetector = ObjectDetector()
    
    # Executor for running blocking inference
    executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1) # YOLO is often not thread-safe or uses internal parallelism
    
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    
    # Register signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Worker ready. Waiting for jobs...")
    
    while not shutdown_event.is_set():
        try:
            # 1. Get Job
            job_info: Optional[Tuple[Any, Dict[str, Any]]] = await consumer.get_next_job()
            
            if not job_info:
                continue
                
            kafka_msg, job_data = job_info
            
            # Use Pydantic to validate incoming task
            try:
                frame_task = FrameTask(**job_data)
            except Exception as e:
                logger.error(f"Invalid FrameTask received: {e}")
                await consumer.acknowledge(kafka_msg)
                continue
                
            video_id: str = frame_task.video_id
            frame_path: str = frame_task.frame_path
            frame_idx: int = frame_task.frame_index
            expected_hash: str = frame_task.frame_hash
            
            logger.info(f"Processing frame {frame_idx} for video {video_id}")
            
            # --- Hash Verification ---
            if expected_hash:
                try:
                    with open(frame_path, "rb") as f:
                        actual_hash: str = storage.compute_hash(f.read())
                    if actual_hash != expected_hash:
                        logger.error(f"CORRUPTION DETECTED: Hash mismatch for frame {frame_idx} of video {video_id}. "
                                     f"Expected: {expected_hash}, Actual: {actual_hash}")
                        # Acknowledge to drop it so it's not retried indefinitely in PEL
                        await consumer.acknowledge(kafka_msg)
                        continue
                except Exception as e:
                    logger.error(f"Failed to read/verify hash for frame {frame_path}: {e}")
                    await asyncio.sleep(1)
                    continue
            # --------------------------
            
            # 2. Run Inference (Blocking CPU bound)
            detections: List[DetectionSchema] = await loop.run_in_executor(
                executor, 
                detector.process_frame, 
                frame_path
            )
            
            # 3. Save to DB
            async with AsyncSessionLocal() as session:
                # Convert Pydantic models to dicts for JSON storage
                detections_data: List[Dict[str, Any]] = [d.model_dump(by_alias=True) for d in detections]
                
                result = DetectionResult(
                    video_id=video_id,
                    frame_path=frame_path,
                    frame_index=frame_idx,
                    detections=detections_data
                )
                session.add(result)
                await session.commit()
                
            logger.info(f"Saved {len(detections)} detections for frame {frame_idx}")
            
            # 4. Acknowledge (Commit Offset)
            await consumer.acknowledge(kafka_msg)
            
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(1)

    logger.info("Inference worker shutting down.")
    await consumer.stop()
    executor.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())
