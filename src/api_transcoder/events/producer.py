from aiokafka import AIOKafkaProducer
from typing import Any, List, Optional
from uuid import UUID
import json


class KafkaProducerWrapper:
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
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
        """Get the number of partitions for the topic."""
        if not self._started:
            raise RuntimeError("Producer not started.")
        partitions = await self.producer.partitions_for(self.topic)
        return len(partitions)


    async def notify_workers(self, job_id: UUID, chunk_keys: List[str]):
        """
        Distribute chunks across partitions for parallel processing.
        Each chunk goes to a different partition (round-robin).
        """
        if not self._started:
            await self.start()

        partition_count = await self.get_partition_count()

        for index, chunk_key in enumerate(chunk_keys):
            # Distribute chunks across partitions
            partition = index % partition_count

            message = {
                "job_id": str(job_id),
                "chunk_s3_key": chunk_key,
                "chunk_index": index,
                "total_chunks": len(chunk_keys),
            }

            await self.send(
                value=json.dumps(message).encode(),
                key=None,  # No key to avoid grouping
                partition=partition,  # Explicit partition assignment
            )