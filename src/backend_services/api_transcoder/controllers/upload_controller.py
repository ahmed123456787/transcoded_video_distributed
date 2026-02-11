from fastapi import APIRouter, Depends, status
from uuid import UUID
from api_transcoder.schema import (
    VideoUploadRequest, 
    VideoUploadedResponse as UploadResponse, 
    TranscodeResponse, 
    JobSchema,
    JobDeleteResponse,
    ApiResponse
)

from api_transcoder.services.video_service import video_service
from api_transcoder.database import get_db
from api_transcoder.services.upload_service import UploadService
from api_transcoder.services.transcoding_service import TranscodingOrchestrator
from api_transcoder.services.job_service import job_service
from api_transcoder.services.chunking_service import chunking_service
from api_transcoder.exceptions.exceptions import ResourceNotFoundError


router = APIRouter()


def get_upload_service():
    return UploadService()


@router.post("/video-signedUrl", response_model=ApiResponse[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_video(
    payload: VideoUploadRequest,
    db=Depends(get_db),
    upload_service: UploadService = Depends(get_upload_service),
):
    video_id, upload_url = upload_service.request_upload(db, payload.filename)
    return ApiResponse(
        success=True,
        message="Upload URL generated successfully",
        data=UploadResponse(video_id=video_id, upload_url=upload_url)
    )


@router.get("/videos", response_model=ApiResponse[list[dict]])
async def list_videos(db=Depends(get_db)):
    videos = video_service.get_all(db).all()
    return ApiResponse(
        success=True,
        message="Videos retrieved successfully",
        data=UploadResponse(videos)
    )


@router.post("/job-launch", response_model=ApiResponse[TranscodeResponse])
async def launch_transcode(video_id: UUID, db=Depends(get_db)):
    orchestrator = TranscodingOrchestrator()
    job_id, chunk_count = await orchestrator.start_transcoding(db, video_id)
    return ApiResponse(
        success=True,
        message="Transcoding job started successfully",
        data=TranscodeResponse(video_id=video_id, job_id=job_id, chunks=chunk_count)
    )


@router.get("/jobs", response_model=ApiResponse[list[JobSchema]])
async def list_jobs(db=Depends(get_db)):
    jobs = job_service.get_all(db).all()
    return ApiResponse(
        success=True,
        message="Jobs retrieved successfully",
        data=jobs
    )


@router.delete("/jobs/{job_id}", response_model=ApiResponse[JobDeleteResponse], status_code=status.HTTP_200_OK)
async def delete_job(job_id: UUID, db=Depends(get_db)):
    job = job_service.get(db, id=job_id)
    if not job:
        raise ResourceNotFoundError(f"Job with ID {job_id} not found")
    
    job_service.delete(db, id=job_id)
    return ApiResponse(
        success=True,
        message=f"Job {job_id} deleted successfully",
        data=JobDeleteResponse(job_id=job_id)
    )


@router.get("/chunk-jobs", response_model=ApiResponse[list[dict]])
async def list_chunk_jobs(db=Depends(get_db)):
    chunk_jobs = chunking_service.get_all(db).all()
    return ApiResponse(
        success=True,
        message="Chunk jobs retrieved successfully",
        data=chunk_jobs
    )