from api_transcoder.storage.minio_client import MinioClient
from minio.error import S3Error


class MinioService:
    def __init__(self):
        self._client = MinioClient()

    def upload_file(self, file_path: str, object_name: str):
        return self._client.upload_file(file_path, object_name)

    def get_presigned_put_url(self, object_name: str, expiry: int = 3600) -> str:
        return self._client.generate_presigned_put_url(object_name, expiry)

    def get_presigned_get_url(self, object_name: str, expiry: int = 3600) -> str:
        return self._client.generate_presigned_get_url(object_name, expiry)

    def file_exists(self, object_name: str) -> bool:
        try:
            self._client.client.stat_object(self._client.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
                return False
            raise


# Singleton instance for convenience
minio_service = MinioService()