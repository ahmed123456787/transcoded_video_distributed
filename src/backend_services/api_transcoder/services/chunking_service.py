from pathlib import Path
from typing import List, Optional
import subprocess
import os
from uuid import UUID, uuid4
from sqlalchemy.orm import Session


from api_transcoder.storage.minio_client import MinioClient
from api_transcoder.services.base_service import BaseService
from api_transcoder.models import JobChunk
from api_transcoder.schema import JobChunkCreateSchema, JobChunkUpdateSchema




class ChunkingService(BaseService[JobChunk, JobChunkCreateSchema, JobChunkUpdateSchema]):
    def __init__(self):
        super().__init__(JobChunk)
        self.minio_client = MinioClient()


    def split_by_seconds(self, input_path: str, target_seconds: int, work_dir: str) -> List[str]:
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        output_pattern = str(Path(work_dir) / "chunk_%03d.ts")
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(target_seconds),
            "-reset_timestamps", "1",
            output_pattern,
        ]
        subprocess.run(cmd, check=True)
        return sorted(str(p) for p in Path(work_dir).glob("chunk_*.ts"))


    def split_from_minio(self, object_key: str, target_seconds: int, work_dir: str) -> List[str]:
        """
        Download video from MinIO to local temp, split into chunks.
        """
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        output_pattern = str(Path(work_dir) / "chunk_%03d.ts")
        
        # Download file from MinIO to local temp
        local_input = str(Path(work_dir) / "input_video.mp4")
        self.minio_client.download_file(object_key, local_input)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", local_input,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(target_seconds),
            "-reset_timestamps", "1",
            output_pattern,
        ]
        subprocess.run(cmd, check=True)
        
        try:
            os.remove(local_input)
        except OSError:
            pass
        
        return sorted(str(p) for p in Path(work_dir).glob("chunk_*.ts"))


    

    def upload_chunks_to_minio(self, chunk_paths: List[str], object_prefix: str) -> List[str]:
        """
        Upload local chunk files to MinIO under object_prefix and remove local files.
        Returns list of object keys stored in MinIO.
        """
        object_keys: List[str] = []
        for p in chunk_paths:
            name = Path(p).name
            key = f"{object_prefix}/{name}"
            self.minio_client.upload_file(file_path=p, object_name=key)
            object_keys.append(key)
            try:
                os.remove(p)
            except OSError:
                pass
        return object_keys
    

    def persist_chunks(self, db: Session, *, job_id: UUID, object_keys: List[str]) -> List[JobChunk]:
        """
        Create JobChunk rows using BaseService.create.
        """
        created: List[JobChunk] = []
        for key in object_keys:
            payload = JobChunkCreateSchema(
                id=uuid4(),
                job_id=job_id,
                chunk_s3_key=key,
            )
            jc = self.create(db, obj_in=payload)
            created.append(jc)
        return created
    

    def create_and_store_chunks(
        self,
        db: Session,
        *,
        job_id: UUID,
        source_object_key: str, 
        target_seconds: int,
        object_prefix: str,
        work_dir: Optional[str] = None,
    ) -> List[JobChunk]:
        """
        Stream from MinIO, split locally, upload chunks to MinIO, and persist JobChunk records.
        """
        tmp_dir = work_dir or f"/tmp/{job_id}"
        
        # Stream directly from MinIO and split
        local_chunks = self.split_from_minio(source_object_key, target_seconds, tmp_dir)
        object_keys = self.upload_chunks_to_minio(local_chunks, object_prefix)
        return self.persist_chunks(db, job_id=job_id, object_keys=object_keys)
    

chunking_service = ChunkingService()