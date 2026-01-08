from fastapi import APIRouter, Depends, status
from uuid import  UUID
from src.schema import VideoUploadedResponse, VideoUpdate, VideoUploadRequest
from src.models import VideoStatus
from src.services.storage_service import  check_file_is_uploaded
from src.services.video_service import video_service
from src.database import get_db
from src.services.storage_service import UploadService

router = APIRouter()


def get_upload_service():
    return UploadService()


@router.post("/upload-video", response_model=VideoUploadedResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    payload: VideoUploadRequest,
    db=Depends(get_db),
    upload_service: UploadService = Depends(get_upload_service),
):
    video_id, upload_url = upload_service.request_upload(db, payload.filename)
    return VideoUploadedResponse(
        video_id=video_id,
        upload_url=upload_url,
        message="Upload URL generated"
    )



@router.get("/videos")
async def list_videos(db=Depends(get_db)):
    videos = video_service.get_all(db)
    return {"videos": videos.all()}



@router.post("/transcode-launch")
async def launch_transcode(video_id: UUID, db=Depends(get_db)):
    check_file_is_uploaded(video_id)

    video_obj = VideoUpdate(status=VideoStatus.PROCESSING.value)
    video = video_service.get(db, id=video_id)
    video_service.update(db, db_obj=video, obj_in=video_obj)

    return {"message": "Transcoding started", "video_id": str(video_id)}