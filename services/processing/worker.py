import asyncio
import logging
import signal
import os
from shared.mq import KafkaConsumer, KafkaProducer
from shared.storage import FileSystemStorage
from processing import extract_frames

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Processing Worker...")
    
    # Initialize components
    storage = FileSystemStorage()
    # Consumer for video uploads
    consumer = KafkaConsumer(topic="video-uploads", group_id="processing-group")
    # Producer for frame tasks
    producer = KafkaProducer(topic="frame-tasks")
    
    await consumer.start()
    await producer.start()
    
    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    logger.info("Worker ready to receive jobs...")

    while not shutdown_event.is_set():
        try:
            job_info = await consumer.get_next_job()
            if not job_info:
                # Small sleep to be nice to the CPU if no messages are coming
                await asyncio.sleep(0.1)
                continue
                
            kafka_msg, job_data = job_info
            video_id = job_data.get("video_id")
            video_path = job_data.get("video_path")
            
            logger.info(f"Processing video {video_id} at {video_path}")
            
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                await consumer.acknowledge(kafka_msg)
                continue

            # 1. Compute Video Hash (useful for downstream detection verification)
            video_hash = storage.compute_file_hash(video_path)
            
            # 2. Extract Frames
            frame_data = extract_frames(video_path, video_id, storage)
            
            # 3. Publish Frame Tasks
            for path, frame_hash in frame_data:
                filename = os.path.basename(path)
                try:
                    # Extract frame index from filename like "120.jpg"
                    frame_idx = int(os.path.splitext(filename)[0])
                    await producer.publish({
                        "video_id": video_id,
                        "frame_path": path,
                        "frame_index": frame_idx,
                        "frame_hash": frame_hash,
                        "video_hash": video_hash
                    })
                except Exception as e:
                    logger.error(f"Failed to publish frame task: {e}")
            
            logger.info(f"Finished processing video {video_id}. Published {len(frame_data)} frames.")
            
            # 4. Acknowledge Video Task
            await consumer.acknowledge(kafka_msg)
            
            # 5. Cleanup video after extraction
            try:
                storage.delete_video(video_path)
                logger.info(f"Cleaned up source video: {video_path}")
            except Exception as e:
                logger.warning(f"Could not delete video {video_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
            await asyncio.sleep(1)

    await consumer.stop()
    await producer.stop()
    logger.info("Processing worker stopped.")

if __name__ == "__main__":
    asyncio.run(main())
