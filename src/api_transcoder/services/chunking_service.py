from pathlib import Path
from typing import List, Optional
import subprocess
import os
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api_transcoder.storage.minio_client import MinioClient
from src.api_transcoder.services.base_service import BaseService
from src.api_transcoder.models import JobChunk
from src.api_transcoder.schema import JobChunkCreateSchema, JobChunkUpdateSchema





class ChunkingService(BaseService[JobChunk, JobChunkCreateSchema, JobChunkUpdateSchema]):
    def __init__(self):
        super().__init__(JobChunk)

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
    

    def upload_chunks_to_minio(self, chunk_paths: List[str], object_prefix: str) -> List[str]:
        """
        Upload local chunk files to MinIO under object_prefix and remove local files.
        Returns list of object keys stored in MinIO.
        """
        m = MinioClient()
        object_keys: List[str] = []
        for p in chunk_paths:
            name = Path(p).name
            key = f"{object_prefix}/{name}"
            m.upload_file(file_path=p, object_name=key)
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


    def notify_workers():
        pass

    def create_and_store_chunks(
        self,
        db: Session,
        *,
        job_id: UUID,
        local_input_path: str,
        target_seconds: int,
        object_prefix: str,
        work_dir: Optional[str] = None,
    ) -> List[JobChunk]:
        """
        Split locally, upload to MinIO, and persist JobChunk records.
        """
        tmp_dir = work_dir or f"/tmp/{job_id}"
        print(local_input_path, "  test")
        local_chunks = self.split_by_seconds(local_input_path, target_seconds, tmp_dir)
        object_keys = self.upload_chunks_to_minio(local_chunks, object_prefix)
        return self.persist_chunks(db, job_id=job_id, object_keys=object_keys)