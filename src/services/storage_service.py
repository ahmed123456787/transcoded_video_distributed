from src.storage.minio_client import MinioClient
import uuid
from datetime import timedelta
from minio.error import S3Error
from src.services.video_service import video_service
from pathlib import Path
from uuid import uuid4
from src.models import VideoStatus
from src.schema import VideoCreateSchema
from src.exceptions.exceptions import UnsupportedFileTypeError


def upload_video_to_minio(file_path: str, object_name: str) :
    minio_client = MinioClient()
    return minio_client.upload_file(file_path, object_name)



def generate_object_name(extension: str) -> str: 
    id = str(uuid.uuid4())
    return  f"videos/{id}.{extension}"


def get_presigned_url(object_name: str, expiry: int = 3600) -> str:
    """Generate a presigned URL for uploading an object to MinIO."""
    minio_client = MinioClient()
    return minio_client.client.presigned_put_object(
        minio_client.bucket_name,
        object_name,
        expires=timedelta(seconds=expiry)
    )



def check_file_is_uploaded(object_name: str) -> bool:
    """
    Return True if the object exists in MinIO, False otherwise.
    object_name is the key you generated (e.g., 'videos/<uuid>').
    """
    minio = MinioClient()
    try:
        minio.client.stat_object(minio.bucket_name, object_name)
        return True
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
            return False
        raise





ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov"}

class UploadService:
    def request_upload(self, db, filename: str):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

        object_name = generate_object_name(ext.lstrip("."))  # keep storage key independent from filename
        presigned_url = get_presigned_url(object_name)

        video_obj = VideoCreateSchema(
            id=uuid4(),
            original_filename=filename,
            s3_bucket="videos",
            presigned_url=object_name,  # NOTE: this seems to store the object key, not the URL
            status=VideoStatus.WAITING_UPLOAD.value
        )
        video_service.create(db, obj_in=video_obj)

        return video_obj.id, presigned_url