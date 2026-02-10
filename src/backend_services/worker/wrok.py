from worker.consumer import ChunkTranscodingConsumer
from common.message_types import ChunkTranscodingMessage
from api_transcoder.storage.minio_client import MinioClient
import asyncio
import json 
from logging import basicConfig, getLogger, INFO


logger = getLogger(__name__)


KAFKA_BOOTSTRAP_SERVERS = "kafka:9093"
KAFKA_TOPIC = "video-chunks"
KAFKA_GROUP_ID = "chunk-transcoding-group"


"""
Processing chunk transcoding message: ConsumerRecord(topic='video-chunks', partition=0, offset=43, 
                                                     timestamp=1770670893694, timestamp_type=0, key=None, 
value=b'{"id": "5a0713f1-18b2-4053-8a61-71fe001303b1", "chunk_index": 40, "target_format": "mp4", "resolution": "1080p", "bitrate": 5000, ' \
'"chunk_s3_key": "chunks/185bbda3-5097-4117-85bc-93b92e3c9a1b/chunk_040.ts", ' \
'"total_chunks": 63}', checksum=None, serialized_key_size=-1, serialized_value_size=225, headers=())
"""


async def process_message( msg:dict ):
    msg_data = json.loads(msg.decode('utf-8'))
    chunk_msg = ChunkTranscodingMessage(**msg_data)

    logger.info(chunk_msg)
    source_bucket = "videos"
    source_key = chunk_msg.chunk_s3_key

    output_bucket = "transcoded"
    output_key = f"chunk_{chunk_msg.chunk_index:03}.mp4"

    # Start ffmpeg (stdin + stdout are pipes)
    ffmpeg = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", "pipe:0",
        "-vf", "scale=1920:1080",
        "-b:v", "5000k",
        "-f", "mp4",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    minio = MinioClient()
    # Stream from MinIO → ffmpeg.stdin
    response = minio.internal_client.get_object(source_bucket, source_key)

    try:
        for chunk in response.stream(1024 * 1024):  # 1 MB chunks
            ffmpeg.stdin.write(chunk)
            await ffmpeg.stdin.drain()

        ffmpeg.stdin.close()

        # Upload ffmpeg stdout directly to MinIO
        minio.internal_client.put_object(
            output_bucket,
            output_key,
            ffmpeg.stdout,
            length=-1,
            part_size=10 * 1024 * 1024
        )

        await ffmpeg.wait()

    finally:
        response.close()
        response.release_conn()



async def main():

    # create the consumer instance. 
    consumer = ChunkTranscodingConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        topic=KAFKA_TOPIC,
        group_id=KAFKA_GROUP_ID
    )
    try: 
        await consumer.start()
        # consume messages with a simple print callback for demonstration
        await consumer.consume(process_message)
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        await consumer.stop()




if __name__ == "__main__":
    asyncio.run(main())
