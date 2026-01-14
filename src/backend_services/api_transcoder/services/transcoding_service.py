from uuid import UUID, uuid4
from pathlib import Path
from sqlalchemy.orm import Session

from api_transcoder.models import VideoStatus, Resolution, JobStatus
from api_transcoder.schema import VideoUpdate, JobCreateSchema
from api_transcoder.services.video_service import video_service
from api_transcoder.services.job_service import JobService
from api_transcoder.services.chunking_service import ChunkingService
from api_transcoder.events.producer import KafkaProducerWrapper
from api_transcoder.config.base_config import settings
from logging import getLogger

logger = getLogger(__name__)


class TranscodingOrchestrator:
    def __init__(self):
        self.job_service = JobService()
        self.chunking_service = ChunkingService()



    async def start_transcoding(self, db: Session, video_id: UUID):
        # Get video record
        video = video_service.get(db, id=video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Create job
        job_payload = JobCreateSchema(
            id=uuid4(),
            video_id=video.id,
            resolution=Resolution.R720P,
            s3_output_key=f"transcoded/{video.id}/output_720p.mp4",
            status=JobStatus.PENDING,
        )
        job = self.job_service.create(db, obj_in=job_payload)

        # Use the video's S3 key directly - no download needed
        chunks = self.chunking_service.create_and_store_chunks(
            db,
            job_id=job.id,
            source_object_key=video.presigned_url,  # Pass the MinIO object key
            target_seconds=60,
            object_prefix=f"chunks/{job.id}",
        )
        # Notify workers via Kafka
        await self._notify_workers(job_id=job.id, chunks=chunks)
        return job.id, len(chunks)


    async def _notify_workers(self, job_id: UUID, chunks):
        logger.info("Testing hello",job_id)
        chunk_keys = [c.chunk_s3_key for c in chunks]
        async with KafkaProducerWrapper(
            topic="video-chunks"
        ) as producer:
            await producer.notify_workers(job_id=job_id, chunk_keys=chunk_keys)