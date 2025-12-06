from fastapi import APIRouter, File, UploadFile,Response
from src.schema import VideoUploadResponse
from src.services.storage_service import upload_video_to_minio
import uuid

router = APIRouter()


@router.post("/upload-video",response_model=VideoUploadResponse)
def upload_video(video: UploadFile = File(...)):

    #check the extension of the file
    if not video.filename.endswith(('.mp4', '.avi', '.mov')):
        return Response(content="Unsupported file type",status_code=400)
    

    # Upload to MinIO storage

    video_id = str(uuid.uuid4())
    
