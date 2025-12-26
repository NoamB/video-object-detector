import json
import redis
import os

class RedisProducer:
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 0):
        # Allow env var override for flexibility
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", port))
        
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.queue_key = "queue:frames"

    def publish_frame(self, video_id: str, frame_path: str, frame_index: int):
        """
        Push a frame task to the Redis queue.
        """
        message = {
            "video_id": video_id,
            "frame_path": frame_path,
            "frame_index": frame_index,
            "timestamp": "TODO" # Could add timestamp if needed
        }
        # LPUSH adds to the head of the list. 
        # For a FIFO queue, we usually use RPUSH (tail) and LPOP/BLPOP (head).
        # Or LPUSH (head) and RPOP (tail).
        # The Reliable Queue pattern often uses BRPOPLPUSH (pops from tail/right of source).
        # So we should add to the LEFT (HEAD) -> LPUSH.
        # queue: Head [Newest ... Oldest] Tail
        # BRPOPLPUSH pops from RIGHT (Tail - Oldest) -> FIFO.
        # Yes, LPUSH is correct for Producer if Consumer pops from Right.
        
        self.client.lpush(self.queue_key, json.dumps(message))
