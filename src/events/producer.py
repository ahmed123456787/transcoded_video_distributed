from aiokafka import AIOKafkaProducer
from typing import Any

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
        **send_kwargs
    ):
       
        if not self._started:
            raise RuntimeError("Producer not started. Call .start() before send().")

        # send message and wait for acknowledgement
        future = await self.producer.send_and_wait(self.topic, value=value, key=key, **send_kwargs)
        return future
