from src.storage.minio_client import MinioClient
import uuid


def upload_video_to_minio(file_path: str, object_name: str) :
    minio_client = MinioClient()
    return minio_client.upload_file(file_path, object_name)



def generate_object_name(filename:str) -> str: 
    id = str(uuid.uuid4())
    