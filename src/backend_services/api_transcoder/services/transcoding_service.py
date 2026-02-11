from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from api_transcoder.models import Resolution, JobStatus
from api_transcoder.schema import  JobCreateSchema
from api_transcoder.services.video_service import video_service
from api_transcoder.services.job_service import JobService
from api_transcoder.services.chunking_service import chunking_service
from api_transcoder.events.producer import KafkaProducer
from common.redis_client import redis_client



class TranscodingOrchestrator:
    def __init__(self):
        self.job_service = JobService()
        self.chunking_service = chunking_service


    async def start_transcoding(self, db: Session, video_id: UUID):

        video = video_service.get(db, id=video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        job_payload = JobCreateSchema(
            id=uuid4(),
            video_id=video.id,
            resolution=Resolution.R720P,
            s3_output_key=f"transcoded/{video.id}/output_720p.mp4",
            status=JobStatus.PENDING,
        )
        job = self.job_service.create(db, obj_in=job_payload)

        chunks = self.chunking_service.create_and_store_chunks(
            db,
            job_id=job.id,
            source_object_key=video.presigned_url, 
            target_seconds=60,
            object_prefix=f"chunks/{job.id}",
        )
        

        # Set total chunks to know how to merge in the future.
        total_chunks = len(chunks)
        await redis_client.set_total_chunks(str(job.id), total_chunks)
        

        # Now notify workers with both the chunks AND total count
        await self._notify_workers(job_id=job.id, chunks=chunks, total_chunks=total_chunks)
        
        return job.id, total_chunks


    async def _notify_workers(self, job_id: UUID, chunks, total_chunks: int):

        chunk_data = [{"id": c.id, "chunk_s3_key": c.chunk_s3_key} for c in chunks]
        
        async with KafkaProducer(topic="video-chunks") as producer:
            await producer.notify_workers(
                job_id=job_id, 
                chunk_data=chunk_data,
            )