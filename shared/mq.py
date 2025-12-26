import os
import json
import logging
import redis
from redis import asyncio as aioredis
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class RedisProducer:
    """
    Synchronous Redis Producer for Ingestion Service using Streams.
    """
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.stream_key = "stream:frames"

    def publish_frame(self, video_id: str, frame_path: str, frame_index: int, frame_hash: str, video_hash: str):
        message = {
            "video_id": video_id,
            "frame_path": frame_path,
            "frame_index": str(frame_index),
            "frame_hash": frame_hash,
            "video_hash": video_hash
        }
        # XADD to the stream. '*' means auto-generate ID.
        self.client.xadd(self.stream_key, message)

class RedisConsumer:
    """
    Asynchronous Redis Consumer for Detection Worker using Consumer Groups.
    """
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        self.host = host
        self.port = port
        self.db = db
        self.stream_key = "stream:frames"
        self.group_name = "group:detection"
        self.consumer_name = f"worker:{os.uname()[1]}" # Use hostname as identifier
        
        self.client = None

    async def connect(self):
        self.client = aioredis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        logger.info(f"Connected to Redis Streams at {self.host}:{self.port}")
        
        # Ensure Consumer Group exists
        try:
            await self.client.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group {self.group_name}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group already exists.")
            else:
                logger.error(f"Error creating consumer group: {e}")

    async def get_next_job(self) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Reads from the consumer group.
        Returns: (message_id, data_dict) or None
        """
        if not self.client:
            await self.connect()
            
        try:
            # First try reading pending messages for this consumer (PEL)
            # Actually, standard pattern is to read '>' (new messages) 
            # and periodically check pending if we want high reliability.
            # For simplicity, we'll read new messages.
            
            # XREADGROUP GROUP {group} {consumer} COUNT 1 STREAMS {stream} >
            response = await self.client.xreadgroup(
                self.group_name, 
                self.consumer_name, 
                {self.stream_key: ">"}, 
                count=1, 
                block=0
            )
            
            if response:
                stream_name, messages = response[0]
                msg_id, data = messages[0]
                return msg_id, data
                
            return None
        except Exception as e:
            logger.error(f"Redis Stream error: {e}")
            return None

    async def acknowledge(self, message_id: str):
        """
        Acknowledge message processing completion (XACK).
        """
        if not self.client:
            return
        try:
            await self.client.xack(self.stream_key, self.group_name, message_id)
        except Exception as e:
            logger.error(f"Error acknowledging message {message_id}: {e}")
