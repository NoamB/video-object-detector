import os
import json
import asyncio
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class KafkaProducer:
    """
    Asynchronous Kafka Producer.
    """
    def __init__(self, topic: str, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
        self.topic = topic
        self.producer = None

    async def start(self):
        max_retries = 10
        retry_delay = 5
        for i in range(max_retries):
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await self.producer.start()
                logger.info(f"Kafka Producer started, topic: {self.topic}, connected to {self.bootstrap_servers}")
                return
            except Exception as e:
                logger.warning(f"Failed to start Kafka Producer (attempt {i+1}/{max_retries}): {e}")
                if i < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Kafka Producer failed to start.")
                    raise

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def publish(self, message: Dict[str, Any]):
        if not self.producer:
            await self.start()
        await self.producer.send_and_wait(self.topic, message)

class KafkaConsumer:
    """
    Asynchronous Kafka Consumer.
    """
    def __init__(self, topic: str, bootstrap_servers: str = "kafka:9092", group_id: str = "default-group"):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
        self.topic = topic
        self.group_id = group_id
        self.consumer = None

    async def start(self):
        max_retries = 10
        retry_delay = 5
        for i in range(max_retries):
            try:
                self.consumer = AIOKafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=False # Manual commit for reliability
                )
                await self.consumer.start()
                logger.info(f"Kafka Consumer started, topic: {self.topic}, joined group {self.group_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to start Kafka Consumer (attempt {i+1}/{max_retries}): {e}")
                if i < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Kafka Consumer failed to start.")
                    raise

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()

    async def get_next_job(self) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """
        Reads from the consumer group.
        Returns: (message_obj, data_dict) or None
        """
        if not self.consumer:
            await self.start()
            
        try:
            # Consume one message
            async for msg in self.consumer:
                return msg, msg.value
        except Exception as e:
            logger.error(f"Kafka Consumer error: {e}")
            return None

    async def acknowledge(self, message: Any):
        """
        Acknowledge message processing. In Kafka, this means committing the offset.
        """
        if not self.consumer:
            return
        try:
            await self.consumer.commit()
        except Exception as e:
            logger.error(f"Error committing Kafka offset: {e}")
