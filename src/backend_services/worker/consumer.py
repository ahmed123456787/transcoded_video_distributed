import aiokafka
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkTranscodingConsumer():
    """Consumer for chunk transcoding messages from the video-chunks topic."""
    
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.running = False
    
    async def start(self):
        """Start the consumer."""
        # Create the consumer within async context
        self.consumer = aiokafka.AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_interval_ms=600000,      # 10 minutes - allow long transcoding
            session_timeout_ms=120000,         # 2 minutes
            heartbeat_interval_ms=30000,       # 30 seconds
            max_poll_records=1,                # Process one message at a time
            connections_max_idle_ms=540000,    # 9 minutes
        )
        self.running = True
        await self.consumer.start()
        logger.info(f"ChunkTranscodingConsumer started for topic: {self.topic}")
    

    async def consume(self, process_callback):
        try:
            async for msg in self.consumer:
                logger.info(f"Received message on partition {msg.partition}, offset {msg.offset}")
                try:
                    await process_callback(msg)
                    await self.consumer.commit()
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error in consume loop: {e}", exc_info=True)
       
    
    async def stop(self):
        """Stop the consumer."""
        if self.consumer:
            self.running = False
            await self.consumer.stop()
            logger.info("ChunkTranscodingConsumer stopped")



