import redis
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class RedisConsumer:
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        # Allow env var override
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        # We need a standard Redis client (not async) for the blocking call 
        # inside a thread or using run_in_executor, OR we can use aioredis (now redis.asyncio).
        # Let's use redis.asyncio for full async compatibility.
        # But for 'brpoplpush' it blocks.
        # If we use strict asyncio, we should use `redis.asyncio` and `await client.brpoplpush`.
        # However, redis-py 5.x supports asyncio via `from redis import asyncio as aioredis`
        
        self.host = host
        self.port = port
        self.db = db
        self.queue_key = "queue:frames"
        self.processing_key = "queue:processing"
        
        self.client = None

    async def connect(self):
        from redis import asyncio as aioredis
        self.client = aioredis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        logger.info(f"Connected to Redis at {self.host}:{self.port}")

    async def get_next_job(self) -> Optional[str]:
        """
        Wait for a job using BRPOPLPUSH.
        Atomically moves from queue -> processing.
        Returns the raw JSON string.
        """
        if not self.client:
            await self.connect()
            
        try:
            # brpoplpush(src, dst, timeout=0) -> returns item or None
            # 0 means block indefinitely.
            job_data = await self.client.brpoplpush(self.queue_key, self.processing_key, timeout=0)
            return job_data
        except Exception as e:
            logger.error(f"Redis error: {e}")
            return None

    async def complete_job(self, job_data: str):
        """
        Remove the job from the processing queue, signifying completion.
        """
        if not self.client:
            return
            
        try:
            # Remove 1 occurrence of job_data from processing list
            await self.client.lrem(self.processing_key, 1, job_data)
        except Exception as e:
            logger.error(f"Error completing job: {e}")
