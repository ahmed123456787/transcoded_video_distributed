from worker.consumer import ChunkTranscodingConsumer
from common.message_types import ChunkTranscodingMessage
from api_transcoder.storage.minio_client import MinioClient
import asyncio
import json 
from logging import  getLogger, INFO


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


import io
from concurrent.futures import ThreadPoolExecutor
from functools import partial

async def process_message(msg: dict):
    logger.info(f"Processing chunk transcoding message: {msg}")
    msg_data = json.loads(msg.value.decode('utf-8'))
    chunk_msg = ChunkTranscodingMessage(**msg_data)

    logger.info(chunk_msg)
    source_bucket = "videos"
    source_key = chunk_msg.chunk_s3_key

    output_bucket = "videos"
    output_key = f"transcoded/{chunk_msg.id}/chunk_{chunk_msg.chunk_index:03}.ts"

    minio = MinioClient()
    
    try:
        logger.info(f"Starting transcoding for {source_key}")
        
        # Start ffmpeg
        ffmpeg = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", "pipe:0",
            # Skip unnecessary rescaling - keep original resolution
            # "-vf", "scale=1920:1080",  # REMOVE THIS - too slow!
            # Video encoding - use copy instead of re-encoding
            "-c:v", "libx264",
            "-preset", "superfast",  # Faster than ultrafast for better speed
            "-tune", "fastdecode",
            "-b:v", "3000k",  # Reduce bitrate for faster encoding
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-profile:v", "baseline",  # Simpler profile = faster
            "-level", "3.1",
            # Audio - just copy, don't re-encode
            "-c:a", "copy",
            # Output format
            "-f", "mpegts",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Task 1: Stream input to ffmpeg (run MinIO blocking calls in thread)
        async def stream_input():
            try:
                logger.info(f"Fetching input from MinIO: {source_bucket}/{source_key}")
                
                # Download entire file to memory first (non-blocking)
                loop = asyncio.get_event_loop()
                
                def download_from_minio():
                    response = minio.internal_client.get_object(source_bucket, source_key)
                    data = response.read()  # Read all data at once
                    response.close()
                    response.release_conn()
                    return data
                
                # Run blocking MinIO call in thread executor
                input_data = await loop.run_in_executor(None, download_from_minio)
                logger.info(f"Downloaded {len(input_data)} bytes from MinIO")
                
                # Write to ffmpeg stdin
                ffmpeg.stdin.write(input_data)
                await ffmpeg.stdin.drain()
                logger.info(f"Wrote {len(input_data)} bytes to ffmpeg stdin")
                ffmpeg.stdin.close()
                
            except Exception as e:
                logger.error(f"Error streaming input: {e}", exc_info=True)
                raise
        
        # Task 2: Collect output from ffmpeg stdout
        async def collect_output():
            chunks = []
            total_size = 0
            try:
                while True:
                    chunk = await ffmpeg.stdout.read(1024 * 1024)  # Read 1MB at a time
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size % (10 * 1024 * 1024) == 0:  # Log every 10MB
                        logger.info(f"Collected {total_size} bytes from ffmpeg stdout")
                logger.info(f"Total output collected: {total_size} bytes")
                return b''.join(chunks)
            except Exception as e:
                logger.error(f"Error collecting output: {e}", exc_info=True)
                raise
        
        # Task 3: Collect stderr
        async def collect_stderr():
            try:
                stderr_data = await ffmpeg.stderr.read()
                return stderr_data
            except Exception as e:
                logger.error(f"Error reading stderr: {e}", exc_info=True)
                return b''
        
        # Run all tasks concurrently
        logger.info("Starting concurrent streaming tasks")
        input_task = asyncio.create_task(stream_input())
        output_task = asyncio.create_task(collect_output())
        stderr_task = asyncio.create_task(collect_stderr())
        
        # Wait for all tasks to complete
        output_data, stderr_data = await asyncio.gather(
            output_task,
            stderr_task
        )
        await input_task
        
        # Wait for ffmpeg to finish
        returncode = await ffmpeg.wait()
        
        # Always log stderr
        stderr_text = stderr_data.decode('utf-8', errors='replace')
        logger.info(f"FFmpeg return code: {returncode}")
        logger.info(f"FFmpeg stderr:\n{stderr_text}")
        
        if returncode != 0:
            logger.error(f"FFmpeg failed with return code {returncode}")
            return
        
        if not output_data:
            logger.error("FFmpeg produced no output")
            return
        
        # Upload to MinIO (run in thread executor)
        logger.info(f"Uploading {len(output_data)} bytes to MinIO: {output_bucket}/{output_key}")
        loop = asyncio.get_event_loop()
        
        def upload_to_minio():
            minio.internal_client.put_object(
                output_bucket,
                output_key,
                io.BytesIO(output_data),
                length=len(output_data),
            )
        
        await loop.run_in_executor(None, upload_to_minio)
        
        logger.info(f"✓ Successfully transcoded and uploaded {output_key} ({len(output_data)} bytes)")
        
    except Exception as e:
        logger.error(f"Fatal error processing chunk {chunk_msg.chunk_index}: {e}", exc_info=True)
        # Kill ffmpeg if still running
        try:
            if 'ffmpeg' in locals() and ffmpeg.returncode is None:
                logger.info("Killing ffmpeg process")
                ffmpeg.kill()
                await ffmpeg.wait()
        except:
            pass

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
