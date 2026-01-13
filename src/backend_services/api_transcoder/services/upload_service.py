from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session

from api_transcoder.models import VideoStatus
from api_transcoder.schema import VideoCreateSchema
from api_transcoder.exceptions.exceptions import UnsupportedFileTypeError
from api_transcoder.services.video_service import video_service
from api_transcoder.services.minio_service import MinioService
from api_transcoder.storage.path_generator import generate_raw_object_name


class UploadService:
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov"}

    def __init__(self, minio_service: MinioService = None):
        self._minio = minio_service or MinioService()

    def request_upload(self, db: Session, filename: str) -> tuple[str, str]:
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

        object_name = generate_raw_object_name(ext.lstrip("."))
        presigned_url = self._minio.get_presigned_put_url(object_name)

        video_obj = VideoCreateSchema(
            id=uuid4(),
            original_filename=filename,
            s3_bucket="videos",
            presigned_url=object_name,
            status=VideoStatus.WAITING_UPLOAD.value
        )
        video_service.create(db, obj_in=video_obj)

        return video_obj.id, presigned_url