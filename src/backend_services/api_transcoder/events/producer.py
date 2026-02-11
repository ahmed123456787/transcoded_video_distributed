from aiokafka import AIOKafkaProducer
from typing import Any, List, Optional
from uuid import UUID
import json
from common.message_types import ChunkTranscodingMessage


class KafkaProducerWrapper:
    def __init__(
        self,
        bootstrap_servers: str = "kafka:9093",
        topic: str = None,
        key_serializer = None,
        value_serializer = None,
        **producer_kwargs,
    ):

        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            key_serializer=key_serializer,
            value_serializer=value_serializer,
            **producer_kwargs
        )
        self._started = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        if not self._started:
            await self.producer.start()
            self._started = True

    async def stop(self):
        if self._started:
            await self.producer.stop()
            self._started = False

    async def send(
        self,
        value: Any = None,
        key: Any = None,
        partition: Optional[int] = None,
        **send_kwargs
    ):
        if not self._started:
            raise RuntimeError("Producer not started. Call .start() before send().")

        future = await self.producer.send_and_wait(
            self.topic,
            value=value,
            key=key,
            partition=partition,
            **send_kwargs
        )
        return future


    async def get_partition_count(self) -> int:
        if not self._started:
            raise RuntimeError("Producer not started.")
        partitions = await self.producer.partitions_for(self.topic)
        return len(partitions)


    async def notify_workers(self, job_id: UUID, chunk_data: List[dict], data: Optional[dict] = None):   
        if not self._started:
            await self.start()

        partition_count = await self.get_partition_count()

        for index, chunk_key in enumerate(chunk_data):
            chunk_id = chunk_key["id"]
            chunk_s3_key = chunk_key["chunk_s3_key"]

            # Distribute chunks across partitions
            partition = index % partition_count

            message = ChunkTranscodingMessage(
                job_id=str(job_id),
                id=str(chunk_id),
                chunk_index=index,
                chunk_s3_key=chunk_s3_key,
                target_format="mp4",  # Example format
                resolution="1080p",   # Example resolution
                bitrate=5000          # Example bitrate in kbps
            ).__dict__


            await self.send(
                value=json.dumps(message).encode(),
                key=None,  
                partition=partition,  # Explicit partition assignment
            )
