from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4, UUID
from src.schema import VideoUploadedResponse, VideoCreateSchema, VideoUpdate
from src.models import VideoStatus
from src.services.storage_service import generate_object_name, get_presigned_url, check_file_is_uploaded
from src.services.video_service import video_task_service
from src.database import get_db

router = APIRouter()

@router.post("/upload-video", response_model=VideoUploadedResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(filename: str, db=Depends(get_db)):
    # Check the extension of the file.
    if not filename.endswith(('.mp4', '.avi', '.mov')):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    extension = filename.split('.')[-1]
    object_name = generate_object_name(extension)
    presigned_url = get_presigned_url(object_name)

    video_obj = VideoCreateSchema(
        id=uuid4(),
        original_filename=filename,
        s3_bucket="videos",
        presigned_url=object_name,  
        status=VideoStatus.WAITING_UPLOAD.value
    )
    video_task_service.create(db, obj_in=video_obj)

    return VideoUploadedResponse(
        video_id=video_obj.id,
        upload_url=presigned_url,
        message="Upload URL generated"
    )


@router.get("/videos")
async def list_videos(db=Depends(get_db)):
    videos = video_task_service.get_all(db)
    return {"videos": videos.all()}



@router.post("/transcode-launch")
async def launch_transcode(video_id: UUID, db=Depends(get_db)):
    check_file_is_uploaded(video_id)

    video_obj = VideoUpdate(status=VideoStatus.PROCESSING.value)
    video = video_task_service.get(db, id=video_id)
    video_task_service.update(db, db_obj=video, obj_in=video_obj)

    return {"message": "Transcoding started", "video_id": str(video_id)}