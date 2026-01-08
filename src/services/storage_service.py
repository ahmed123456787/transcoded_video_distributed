from src.storage.minio_client import MinioClient
import uuid
from datetime import timedelta


def upload_video_to_minio(file_path: str, object_name: str) :
    minio_client = MinioClient()
    return minio_client.upload_file(file_path, object_name)



def generate_object_name() -> str: 
    id = str(uuid.uuid4())
    return  f"videos/{id}"


def get_presigned_url(object_name: str, expiry: int = 3600) -> str:
    """Generate a presigned URL for uploading an object to MinIO."""
    minio_client = MinioClient()
    return minio_client.client.presigned_put_object(
        minio_client.bucket_name,
        object_name,
        expires=timedelta(seconds=expiry)
    )

# def get_presigned_url_get(object_name: str, expiry: int = 3600) -> str:
#     """Generate a presigned URL for downloading an object from MinIO."""
#     minio_client = MinioClient()
#     return minio_client.client.presigned_get_object(
#         minio_client.bucket_name,
#         object_name,
#         expiry=expiry
#     )