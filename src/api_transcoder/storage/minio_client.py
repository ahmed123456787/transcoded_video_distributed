from minio import Minio
from datetime import datetime
from urllib.parse import urlencode, quote
import hashlib
import hmac
from src.api_transcoder.config.base_config import settings


class MinioClient:

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )
        self.bucket_name = settings.MINIO_BUCKET
        self.external_endpoint = settings.MINIO_EXTERNAL_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY

    def list_buckets(self):
        return self.client.list_buckets()

    def check_bucket_exists(self, bucket_name: str) -> bool:
        return self.client.bucket_exists(bucket_name)

    def upload_file(self, file_path: str, object_name: str):
        if not self.check_bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        return self.client.fput_object(
            self.bucket_name,
            object_name,
            file_path,
        )

    def download_file(self, object_name: str, file_path: str):
        return self.client.fget_object(
            self.bucket_name,
            object_name,
            file_path,
        )

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, date_stamp: str, region: str, service: str) -> bytes:
        k_date = self._sign(("AWS4" + self.secret_key).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, region)
        k_service = self._sign(k_region, service)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _generate_presigned_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        """
        Generate a presigned URL using AWS Signature Version 4.
        """
        region = "us-east-1"
        service = "s3"
        host = self.external_endpoint
        
        # Current time
        t = datetime.utcnow()
        amz_date = t.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = t.strftime("%Y%m%d")
        
        # Credential scope
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        
        # Canonical URI - keep slashes, only encode special characters
        # safe='/' keeps forward slashes unencoded
        canonical_uri = f"/{self.bucket_name}/{quote(object_name, safe='/')}"
        
        # Query parameters
        query_params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": "host",
        }
        canonical_querystring = urlencode(sorted(query_params.items()))
        
        # Canonical headers
        canonical_headers = f"host:{host}\n"
        signed_headers = "host"
        
        # Payload hash (UNSIGNED-PAYLOAD for presigned URLs)
        payload_hash = "UNSIGNED-PAYLOAD"
        
        # Canonical request
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # String to sign
        string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Signing key
        signing_key = self._get_signature_key(date_stamp, region, service)
        
        # Signature
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # Final URL
        url = f"http://{host}{canonical_uri}?{canonical_querystring}&X-Amz-Signature={signature}"
        
        return url
    

    def generate_presigned_put_url(self, object_name: str, expires: int = 3600) -> str:
        return self._generate_presigned_url("PUT", object_name, expires)


    def generate_presigned_get_url(self, object_name: str, expires: int = 3600) -> str:
        return self._generate_presigned_url("GET", object_name, expires)