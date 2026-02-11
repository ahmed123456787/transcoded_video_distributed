import asyncio
import json
import io
from logging import getLogger

from worker.consumer import ChunkTranscodingConsumer
from common.message_types import ChunkTranscodingMessage
from api_transcoder.storage.minio_client import MinioClient
from common.redis_client import redis_client
from minio import Minio


logger = getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "kafka:9093"
KAFKA_TOPIC = "video-chunks"
KAFKA_GROUP_ID = "chunk-transcoding-group"

# FFmpeg configuration
FFMPEG_ARGS = [
    "ffmpeg",
    "-i", "pipe:0",
    "-c:v", "libx264",
    "-preset", "superfast",
    "-tune", "fastdecode",
    "-b:v", "3000k",
    "-maxrate", "3000k",
    "-bufsize", "6000k",
    "-profile:v", "baseline",
    "-level", "3.1",
    "-c:a", "copy",
    "-f", "mpegts",
    "pipe:1",
]

BUCKET_NAME = "videos"


async def download_from_minio(minio_client, bucket, key):
    """Download file from MinIO to memory."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: minio_client.internal_client.get_object(bucket, key).read()
    )


async def upload_to_minio(minio_client, bucket, key, data):
    """Upload bytes to MinIO."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: minio_client.internal_client.put_object(
            bucket, key, io.BytesIO(data), length=len(data)
        )
    )


async def transcode_chunk(input_data):
    """Transcode chunk using ffmpeg."""
    ffmpeg = await asyncio.create_subprocess_exec(
        *FFMPEG_ARGS,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        # Write input and collect output concurrently
        stdout_task = asyncio.create_task(ffmpeg.stdout.read())
        stderr_task = asyncio.create_task(ffmpeg.stderr.read())

        ffmpeg.stdin.write(input_data)
        await ffmpeg.stdin.drain()
        ffmpeg.stdin.close()

        output_data, stderr_data = await asyncio.gather(stdout_task, stderr_task)
        returncode = await ffmpeg.wait()

        if returncode != 0:
            stderr_text = stderr_data.decode('utf-8', errors='replace')
            logger.error(f"FFmpeg failed (code {returncode}):\n{stderr_text}")
            return None

        return output_data

    except Exception:
        if ffmpeg.returncode is None:
            ffmpeg.kill()
            await ffmpeg.wait()
        raise


async def merge_chunks(job_id, output_format="mp4"):
    """Merge all transcoded chunks into final output."""
    import subprocess
    
    chunk_pattern = f"transcoded/{job_id}/chunk_*.ts"
    output_file = f"final_{job_id}.{output_format}"
    
    # Use ffmpeg concat protocol to merge
    cmd = [
        "ffmpeg",
        "-i", f"concat:transcoded/{job_id}/chunk_*.ts",
        "-c", "copy",
        "-f", output_format,
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0:
        logger.info(f"✓ Successfully merged chunks into {output_file}")
        return output_file
    else:
        logger.error(f"Merge failed: {result.stderr.decode()}")
        return None
    



async def process_message(msg: dict):
    """Process a single chunk transcoding message."""
    logger.info(f"Processing chunk transcoding message")

    msg_data = json.loads(msg.value.decode('utf-8'))
    chunk_msg = ChunkTranscodingMessage(**msg_data)
    
    minio = MinioClient()
    
    try:
        source_key = chunk_msg.chunk_s3_key
        logger.info(f"Downloading {source_key}")
        input_data = await download_from_minio(minio, BUCKET_NAME, source_key)
        logger.info(f"Downloaded {len(input_data)} bytes")

        # Transcode
        output_data = await transcode_chunk(input_data)
        if not output_data:
            return

        # Upload result
        output_key = f"transcoded/{chunk_msg.job_id}/chunk_{chunk_msg.chunk_index:03}.ts"
        await upload_to_minio(minio, BUCKET_NAME, output_key, output_data)
        
        logger.info(f"✓ Successfully transcoded {output_key} ({len(output_data)} bytes)")
        
        # Update progress
        await redis_client.increment_completed_chunks(chunk_msg.job_id)

        #merge if completed
        is_complete = await redis_client.is_job_complete(chunk_msg.job_id)
        if is_complete:
            output_file = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: asyncio.run(merge_chunks(chunk_msg.job_id))
            )
            
            # Read the file and upload
            with open(output_file, 'rb') as f:
                file_data = f.read()
            
            await upload_to_minio(minio, BUCKET_NAME, f"transcoded/{chunk_msg.job_id}/final_output.mp4", file_data)
            logger.info(f"✓ Final output uploaded for job {chunk_msg.job_id}")
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_msg.chunk_index}: {e}", exc_info=True)



async def main():
    consumer = ChunkTranscodingConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        topic=KAFKA_TOPIC,
        group_id=KAFKA_GROUP_ID
    )
    
    try:
        await consumer.start()
        await consumer.consume(process_message)
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())