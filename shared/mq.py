import os
import json
import logging
import redis
from redis import asyncio as aioredis
from typing import Optional

logger = logging.getLogger(__name__)

class RedisProducer:
    """
    Synchronous Redis Producer for Ingestion Service.
    """
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.queue_key = "queue:frames"

    def publish_frame(self, video_id: str, frame_path: str, frame_index: int):
        message = {
            "video_id": video_id,
            "frame_path": frame_path,
            "frame_index": frame_index
        }
        # LPUSH to add to Head
        self.client.lpush(self.queue_key, json.dumps(message))

class RedisConsumer:
    """
    Asynchronous Redis Consumer for Detection Worker.
    """
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        self.host = host
        self.port = port
        self.db = db
        self.queue_key = "queue:frames"
        self.processing_key = "queue:processing"
        
        self.client = None

    async def connect(self):
        self.client = aioredis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        logger.info(f"Connected to Redis at {self.host}:{self.port}")

    async def get_next_job(self) -> Optional[str]:
        if not self.client:
            await self.connect()
            
        try:
            # BRPOPLPUSH from Tail (Right)
            return await self.client.brpoplpush(self.queue_key, self.processing_key, timeout=0)
        except Exception as e:
            logger.error(f"Redis error: {e}")
            return None

    async def complete_job(self, job_data: str):
        if not self.client:
            return
        try:
            await self.client.lrem(self.processing_key, 1, job_data)
        except Exception as e:
            logger.error(f"Error completing job: {e}")
