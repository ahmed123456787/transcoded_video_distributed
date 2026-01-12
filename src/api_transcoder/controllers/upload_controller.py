from fastapi import APIRouter, Depends, status
from uuid import  UUID
from src.api_transcoder.schema import VideoUploadedResponse, VideoUpdate, VideoUploadRequest,JobCreateSchema
from src.api_transcoder.models import VideoStatus,Resolution,JobStatus
from src.api_transcoder.services.storage_service import  check_file_is_uploaded 
from src.api_transcoder.services.video_service import video_service
from src.api_transcoder.database import get_db
from src.api_transcoder.services.storage_service import UploadService
from src.api_transcoder.services.job_service import JobService
from src.api_transcoder.services.chunking_service import ChunkingService
from pathlib import Path
from uuid import uuid4


router = APIRouter()


def get_upload_service():
    return UploadService()


@router.post("/video-signedUrl", response_model=VideoUploadedResponse, status_code=status.HTTP_201_CREATED)
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



@router.post("/job-launch")
async def launch_transcode(video_id: UUID, db=Depends(get_db)):
    # check_file_is_uploaded(video_id)

    video = video_service.get(db, id=video_id)
    video_obj = VideoUpdate(status=VideoStatus.PROCESSING.value)
    video_service.update(db, db_obj=video, obj_in=video_obj)

    ext = Path(video.original_filename).suffix or ".mp4"
    # stable key independent of original name
    output_key = f"transcoded/{video_id}/1080p{ext}"

    job_service = JobService()
    job_obj = JobCreateSchema(
        id=uuid4(),
        video_id=video_id,
        resolution=Resolution.R1080P,
        s3_output_key=output_key,
        status=JobStatus.PENDING,
    )
    job_service.create(db, obj_in=job_obj)
    chunking_service = ChunkingService()
    chunking_service.create_and_store_chunks(
        db,
        job_id=job_obj.id,
        local_input_path=f"/tmp/uploads/{video_id}{ext}",
        target_seconds=60,
        object_prefix=f"chunks/{job_obj.id}",
    )
    return {"message": "Transcoding started", "video_id": str(video_id)}