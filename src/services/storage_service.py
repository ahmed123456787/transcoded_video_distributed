from src.storage.minio_client import MinioClient
import uuid
from datetime import timedelta
from minio.error import S3Error


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