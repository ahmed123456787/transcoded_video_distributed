from fastapi import APIRouter, Depends, status
from uuid import  UUID
from api_transcoder.schema import VideoUploadedResponse, VideoUploadRequest, JobSchema
from api_transcoder.services.video_service import video_service
from api_transcoder.database import get_db
from api_transcoder.services.upload_service import UploadService
from api_transcoder.services.transcoding_service import TranscodingOrchestrator
from api_transcoder.services.job_service import job_service
from api_transcoder.services.chunking_service import chunking_service


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
    orchestrator = TranscodingOrchestrator()
    job_id, chunk_count = await orchestrator.start_transcoding(db, video_id)
    return {"message": "Transcoding started", "video_id": str(video_id), "job_id": str(job_id), "chunks": chunk_count}



@router.get("/jobs", response_model=list[JobSchema])
async def list_jobs(db=Depends(get_db)):
    jobs = job_service.get_all(db).all()
    return jobs


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: UUID, db=Depends(get_db)):
    job_service.delete(db, id=job_id)
    return {"message": f"Job {job_id} deleted"}


@router.get("/chunk-jobs")
async def list_chunk_jobs(db=Depends(get_db)):
    chunk_jobs = chunking_service.get_all(db).all()
    return {"chunk_jobs": chunk_jobs}