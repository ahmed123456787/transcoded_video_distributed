from src.api_transcoder.storage.minio_client import MinioClient
import uuid
from datetime import timedelta
from minio.error import S3Error
from src.api_transcoder.services.video_service import video_service
from pathlib import Path
from uuid import uuid4
from src.api_transcoder.models import VideoStatus
from src.api_transcoder.schema import VideoCreateSchema
from src.api_transcoder.exceptions.exceptions import UnsupportedFileTypeError


# Storage path prefixes
class StoragePaths:
    RAW = "raw"
    CHUNKS = "chunks"
    TRANSCODED = "transcoded"


def upload_video_to_minio(file_path: str, object_name: str):
    minio_client = MinioClient()
    return minio_client.upload_file(file_path, object_name)


def generate_object_name(extension: str, prefix: str = StoragePaths.RAW) -> str:
    """
    Generate object name with folder prefix.
    Examples:
        - raw/uuid.mp4 (for uploads)
        - transcoded/uuid/720p.mp4 (for transcoded)
    """
    id = str(uuid.uuid4())
    return f"{prefix}/{id}.{extension}"


def generate_raw_object_name(extension: str) -> str:
    """Generate object name for raw uploads: raw/uuid.mp4"""
    id = str(uuid.uuid4())
    return f"{StoragePaths.RAW}/{id}.{extension}"


def generate_chunk_object_name(video_id: str, chunk_index: int, extension: str = "mp4") -> str:
    """Generate object name for chunks: chunks/video_id/chunk_000.mp4"""
    return f"{StoragePaths.CHUNKS}/{video_id}/chunk_{chunk_index:03d}.{extension}"


def generate_transcoded_object_name(video_id: str, quality: str, extension: str = "mp4") -> str:
    """Generate object name for transcoded: transcoded/video_id/720p.mp4"""
    return f"{StoragePaths.TRANSCODED}/{video_id}/{quality}.{extension}"


def get_presigned_url(object_name: str, expiry: int = 3600) -> str:
    """Generate a presigned URL for uploading an object to MinIO."""
    minio_client = MinioClient()
    return minio_client.generate_presigned_put_url(object_name, expiry)


def get_presigned_download_url(object_name: str, expiry: int = 3600) -> str:
    """Generate a presigned URL for downloading an object from MinIO."""
    minio_client = MinioClient()
    return minio_client.generate_presigned_get_url(object_name, expiry)


def check_file_is_uploaded(object_name: str) -> bool:
    """
    Return True if the object exists in MinIO, False otherwise.
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

        # Store raw uploads in raw/ folder
        object_name = generate_raw_object_name(ext.lstrip("."))
        presigned_url = get_presigned_url(object_name)

        video_obj = VideoCreateSchema(
            id=uuid4(),
            original_filename=filename,
            s3_bucket="videos",
            presigned_url=object_name,
            status=VideoStatus.WAITING_UPLOAD.value
        )
        video_service.create(db, obj_in=video_obj)

        return video_obj.id, presigned_url


upload_service = UploadService()