from worker.consumer import ChunkTranscodingConsumer
from common.message_types import ChunkTranscodingMessage

import asyncio


# define the const variable 

KAFKA_BOOTSTRAP_SERVERS = "kafka:9093"
KAFKA_TOPIC = "video-chunks"
KAFKA_GROUP_ID = "chunk-transcoding-group"


async def process_message( msg:ChunkTranscodingMessage ):
    # Implement your message processing logic here
    print(f"Processing chunk transcoding message: {msg}")


async def main():

    # create the consumer instance. 
    consumer = ChunkTranscodingConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        topic=KAFKA_TOPIC,
        group_id=KAFKA_GROUP_ID
    )
    try: 
        # start the consumer
        await consumer.start()
        # consume messages with a simple print callback for demonstration
        await consumer.consume(process_message)
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
