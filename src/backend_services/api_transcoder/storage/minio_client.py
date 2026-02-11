from minio import Minio
from datetime import timedelta
from api_transcoder.config.base_config import settings
from logging import getLogger
from urllib.parse import urlparse

logger = getLogger(__name__)

class MinioClient:
    def __init__(self):
        # 1. Internal Client 
        internal_host = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        self.internal_client = Minio(
            internal_host,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_ENDPOINT.startswith("https")
        )

        # 2. Signer Client 
        ext_endpoint = settings.MINIO_EXTERNAL_ENDPOINT
        if not ext_endpoint.startswith(('http://', 'https://')):
            ext_endpoint = f"http://{ext_endpoint}"
            
        parsed_external = urlparse(ext_endpoint)
        
        self.signer_client = Minio(
            parsed_external.netloc, 
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=parsed_external.scheme == "https",
            region="us-east-1"  
        )

        self.bucket_name = settings.MINIO_BUCKET

    # --- Internal Operations (Use internal_client) ---

    def list_buckets(self):
        return self.internal_client.list_buckets()

    def check_bucket_exists(self, bucket_name: str) -> bool:
        return self.internal_client.bucket_exists(bucket_name)

    def upload_file(self, file_path: str, object_name: str):
        if not self.check_bucket_exists(self.bucket_name):
            self.internal_client.make_bucket(self.bucket_name)
        
        return self.internal_client.fput_object(
            self.bucket_name,
            object_name,
            file_path,
        )

    def download_file(self, object_name: str, file_path: str):
        return self.internal_client.fget_object(
            self.bucket_name,
            object_name,
            file_path,
        )

    # --- External URL Generation (Use signer_client) ---

    def generate_presigned_put_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generates a PUT URL signed with the external hostname so the hash matches.
        """
        print(object_name)
        url = self.signer_client.get_presigned_url(
            "PUT",
            self.bucket_name,
            object_name,
            expires=timedelta(seconds=expires),
        )
        logger.info(f"Generated External PUT URL: {url}")
        return url

    def generate_presigned_get_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generates a GET URL signed with the external hostname so the hash matches.
        """
        url = self.signer_client.get_presigned_url(
            "GET",
            self.bucket_name,
            object_name,
            expires=timedelta(seconds=expires),
        )
        logger.info(f"Generated External GET URL: {url}")
        return url