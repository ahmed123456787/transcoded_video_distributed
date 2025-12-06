from minio import Minio
from src.config.base_config import BaseConfig

class MinioClient:

    def __init__(self):
        self.client = Minio(
            BaseConfig.MINIO_ENDPOINT,
            access_key=BaseConfig.MINIO_ACCESS_KEY,
            secret_key=BaseConfig.MINIO_SECRET_KEY,
        )
        self.bucket_name = BaseConfig.MINIO_BUCKET
    

    def list_buckets(self):
        return self.client.list_buckets()
    

    def check_bucket_exists(self, bucket_name: str) -> bool:
        return self.client.bucket_exists(bucket_name)


    def upload_file(self, file_path: str, object_name: str) :
        if not self.check_bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        return self.client.fput_object(
            self.bucket_name,
            object_name,
            file_path,
        )


    def download_file(self, object_name: str, file_path: str) :
        return self.client.fget_object(
            self.bucket_name,
            object_name,
            file_path,
        )
    
