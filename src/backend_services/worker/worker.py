import json
import asyncio
import logging
from pathlib import Path
import subprocess

from common.redis_client import redis_client
from common.message_types import ChunkTranscodingMessage
from worker.consumer import ChunkTranscodingConsumer
from api_transcoder.storage.minio_client import MinioClient
from api_transcoder.config.base_config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscodingWorker:
    """Worker service that transcodes video chunks to target resolution."""
    
    def __init__(self):
        self.minio_client = MinioClient()
        self.work_dir = Path("/tmp/transcoding_worker")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
    def get_job_work_dir(self, job_id: str) -> Path:
        """Get working directory for a specific job."""
        job_dir = self.work_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def download_chunk(self, chunk_s3_key: str, job_dir: Path) -> Path:
        """Download chunk from MinIO to local directory."""
        try:
            local_path = job_dir / Path(chunk_s3_key).name
            logger.info(f"Downloading chunk from {chunk_s3_key} to {local_path}")
            self.minio_client.download_file(chunk_s3_key, str(local_path))
            return local_path
        except Exception as e:
            logger.error(f"Error downloading chunk: {e}")
            raise
    
    def transcode_to_resolution(
        self,
        input_path: Path,
        output_path: Path,
        resolution: str = "1080p",
        bitrate: int = 5000
    ) -> bool:
        """Transcode chunk to target resolution."""
        try:
            # Parse resolution (e.g., "1080p" -> 1080)
            height = int(resolution.rstrip('p'))
            
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", str(input_path),
                "-vf", f"scale=-1:{height}",  # Scale to target height, maintain aspect ratio
                "-c:v", "libx264",
                "-preset", "fast",  # fast for worker speed
                "-b:v", f"{bitrate}k",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path),
            ]
            
            logger.info(f"Transcoding {input_path} to {resolution} @ {bitrate}kbps")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully transcoded: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Transcoding error: {e}")
            raise
    
    def upload_transcoded_chunk(self, local_path: Path, chunk_id: str, job_id: str) -> str:
        """Upload transcoded chunk to MinIO."""
        try:
            # Generate S3 key for transcoded chunk
            chunk_index = int(Path(local_path).stem.split("_")[-1])
            s3_key = f"transcoded/{job_id}/chunk_{chunk_index:03d}.mp4"
            
            logger.info(f"Uploading transcoded chunk to {s3_key}")
            self.minio_client.upload_file(str(local_path), s3_key)
            return s3_key
        except Exception as e:
            logger.error(f"Error uploading transcoded chunk: {e}")
            raise
    
    def cleanup_local_files(self, job_dir: Path):
        """Clean up local temporary files."""
        try:
            import shutil
            if job_dir.exists():
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up working directory: {job_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up directory: {e}")


class VideoMerger:
    """Handles merging transcoded chunks back into a single video."""
    
    def __init__(self):
        self.minio_client = MinioClient()
        self.work_dir = Path("/tmp/video_merge")
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def get_job_merge_dir(self, job_id: str) -> Path:
        """Get merge directory for a specific job."""
        merge_dir = self.work_dir / job_id
        merge_dir.mkdir(parents=True, exist_ok=True)
        return merge_dir
    
    async def download_all_chunks(self, job_id: str, total_chunks: int) -> list[Path]:
        """Download all transcoded chunks from MinIO."""
        chunks = []
        merge_dir = self.get_job_merge_dir(job_id)
        
        try:
            for i in range(total_chunks):
                chunk_key = f"transcoded/{job_id}/chunk_{i:03d}.mp4"
                local_path = merge_dir / f"chunk_{i:03d}.mp4"
                
                logger.info(f"Downloading chunk {i} from {chunk_key}")
                self.minio_client.download_file(chunk_key, str(local_path))
                chunks.append(local_path)
            
            return chunks
        except Exception as e:
            logger.error(f"Error downloading chunks: {e}")
            raise
    
    def create_concat_file(self, chunks: list[Path], concat_file: Path):
        """Create ffmpeg concat demuxer file."""
        try:
            with open(concat_file, 'w') as f:
                for chunk in chunks:
                    # Escape single quotes in paths
                    escaped_path = str(chunk).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            logger.info(f"Created concat file: {concat_file}")
        except Exception as e:
            logger.error(f"Error creating concat file: {e}")
            raise
    
    def merge_chunks(self, chunks: list[Path], output_path: Path) -> bool:
        """Merge chunks using ffmpeg concat demuxer."""
        try:
            merge_dir = output_path.parent
            concat_file = merge_dir / "concat.txt"
            
            self.create_concat_file(chunks, concat_file)
            
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",  # Copy without re-encoding
                str(output_path),
            ]
            
            logger.info(f"Merging {len(chunks)} chunks into {output_path}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully merged chunks: {output_path}")
            
            # Cleanup concat file
            concat_file.unlink(missing_ok=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg merge error: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Merge error: {e}")
            raise
    
    def upload_final_video(self, local_path: Path, job_id: str, s3_output_key: str) -> str:
        """Upload final merged video to MinIO."""
        try:
            logger.info(f"Uploading final video to {s3_output_key}")
            self.minio_client.upload_file(str(local_path), s3_output_key)
            return s3_output_key
        except Exception as e:
            logger.error(f"Error uploading final video: {e}")
            raise
    
    def cleanup_merge_files(self, job_dir: Path):
        """Clean up merge temporary files."""
        try:
            import shutil
            if job_dir.exists():
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up merge directory: {job_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up merge directory: {e}")


class ChunkTranscodingWorker:
    """Main worker orchestrator for chunk transcoding."""
    
    def __init__(self):
        self.transcoder = TranscodingWorker()
        self.merger = VideoMerger()
        self.bootstrap_servers = settings.KAFKA_BROKER
        self.consumer = ChunkTranscodingConsumer(
            bootstrap_servers=self.bootstrap_servers,
            topic="video-chunks",
            group_id="transcoding-workers"
        )
        self.processing_job = None  # Track current job being processed
    
    async def process_chunk(self, message: dict):
        """Process a single chunk: download, transcode, upload, track."""
        try:
            msg_data = json.loads(message.value.decode('utf-8'))
            chunk_msg = ChunkTranscodingMessage(**msg_data)
            
            # Extract job_id from chunk_s3_key (e.g., "chunks/job-id/chunk_000.ts")
            job_id = chunk_msg.chunk_s3_key.split('/')[1]
            self.processing_job = job_id
            job_dir = self.transcoder.get_job_work_dir(job_id)
            
            logger.info(f"Processing chunk {chunk_msg.chunk_index} for job {job_id}")
            
            # IMPORTANT: Ensure Redis is initialized with total_chunks on first message
            job_data = redis_client.client.hgetall(f"job:{job_id}")
            if not job_data or b'total_chunks' not in job_data:
                # First worker to process this job - initialize from message
                if chunk_msg.total_chunks:
                    logger.info(f"Initializing job {job_id} with {chunk_msg.total_chunks} total chunks")
                    await redis_client.set_total_chunks(job_id, chunk_msg.total_chunks)
                else:
                    logger.error(f"No total_chunks in message for job {job_id}")
                    raise ValueError(f"Cannot determine total chunks for job {job_id}")
            
            # Step 1: Download chunk from MinIO
            chunk_path = self.transcoder.download_chunk(chunk_msg.chunk_s3_key, job_dir)
            
            # Step 2: Transcode chunk
            output_filename = f"transcoded_{chunk_msg.chunk_index:03d}.mp4"
            output_path = job_dir / output_filename
            
            self.transcoder.transcode_to_resolution(
                input_path=chunk_path,
                output_path=output_path,
                resolution=chunk_msg.resolution,
                bitrate=chunk_msg.bitrate
            )
            
            # Step 3: Upload transcoded chunk
            transcoded_s3_key = self.transcoder.upload_transcoded_chunk(
                output_path,
                chunk_msg.id,
                job_id
            )
            
            # Step 4: Update Redis - increment completed chunks
            completed_count = await redis_client.increment_completed_chunks(job_id)
            total = int(redis_client.client.hget(f"job:{job_id}", "total_chunks") or 0)
            logger.info(f"Job {job_id}: {completed_count}/{total} chunks completed")
            
            # Step 5: Check if all chunks are complete
            is_complete = await redis_client.is_job_complete(job_id)
            
            if is_complete:
                logger.info(f"All chunks completed for job {job_id}. Starting merge...")
                await self.merge_and_finalize_video(job_id)
                logger.info(f"Job {job_id} merge completed successfully!")
                self.processing_job = None
            
            # Cleanup local chunk files
            chunk_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            self.processing_job = None
            # In production, you might want to publish an error event or update job status
            raise
    
    async def merge_and_finalize_video(self, job_id: str):
        """Merge all transcoded chunks and upload final video."""
        try:
            logger.info(f"Starting merge for job {job_id}")
            
            # Get total chunk count from Redis
            job_data = redis_client.client.hgetall(f"job:{job_id}")
            if not job_data:
                raise ValueError(f"Job {job_id} not found in Redis")
            
            total_chunks = int(job_data[b'total_chunks'])
            
            # Download all chunks
            chunks = await self.merger.download_all_chunks(job_id, total_chunks)
            
            # Merge chunks
            merge_dir = self.merger.get_job_merge_dir(job_id)
            final_output = merge_dir / f"final_video_{job_id}.mp4"
            
            self.merger.merge_chunks(chunks, final_output)
            
            # Upload final video
            s3_output_key = f"transcoded/{job_id}/output_1080p.mp4"
            self.merger.upload_final_video(final_output, job_id, s3_output_key)
            
            logger.info(f"Successfully completed job {job_id}. Final video: {s3_output_key}")
            
            # Update Redis to mark job as complete
            await redis_client.mark_job_complete(job_id)
            
            # Cleanup
            self.merger.cleanup_merge_files(merge_dir)
            self.transcoder.cleanup_local_files(self.transcoder.get_job_work_dir(job_id))
            
        except Exception as e:
            logger.error(f"Error merging video for job {job_id}: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the worker consumer."""
        logger.info("Starting chunk transcoding worker...")
        await self.consumer.start()
        try:
            await self.consumer.consume(self.process_chunk)
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
        finally:
            # Give a moment to ensure commit is processed
            if self.processing_job:
                logger.info(f"Waiting for job {self.processing_job} to complete...")
                await asyncio.sleep(2)
            await self.consumer.stop()
            logger.info("Worker stopped")


async def main():
    """Main entry point for the worker."""
    worker = ChunkTranscodingWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())

