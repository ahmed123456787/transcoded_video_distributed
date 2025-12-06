import aiokafka
from abc import ABC, abstractmethod


class EventConsumer(ABC):

    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = aiokafka.AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False # to ensure messages are processed then ACK kafka
        )
        self.running = False


    async def start(self):
        self.running = True
        await self.consumer.start()


    async def stop(self):
        self.running = False
        await self.consumer.stop()


    async def consume(self):
        try:
            async for msg in self.consumer:
                # process message for each consumed message case (uploaded,chuneked ...)
                await self._process_message(msg)
                await self.consumer.commit()
                if not self.running:
                    break
        except Exception as e:
            pass
            # do not commit offset if error occurs during processing
        finally:
            await self.stop()

    @abstractmethod
    async def _process_message(self, msg): ...



class VideoUploadedConsumer(EventConsumer):
    async def _process_message(self, msg):
        # Implement your message processing logic here
        print(f"Processing message: {msg.value.decode('utf-8')}")


class VideoChunkedConsumer(EventConsumer):
    async def _process_message(self, msg):
        # Implement your message processing logic here
        print(f"Processing chunked video message: {msg.value.decode('utf-8')}")



class VideoTranscodedConsumer(EventConsumer): 
    async def _process_message(self, msg):
        # Implement your message processing logic here
        print(f"Processing transcoded video message: {msg.value.decode('utf-8')}")



class VideoFailedConsumer(EventConsumer):
    async def _process_message(self, msg):
        # Implement your message processing logic here
        print(f"Processing failed video message: {msg.value.decode('utf-8')}")