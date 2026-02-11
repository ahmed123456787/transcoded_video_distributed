from pydantic import BaseModel
from typing import Optional, Generic, TypeVar
from uuid import UUID
from api_transcoder.models import Resolution
from api_transcoder.models import JobStatus


class VideoCreateSchema(BaseModel):
    id: UUID
    original_filename: str
    status: str
    s3_bucket: str
    presigned_url: str



class VideoUpdate(BaseModel):
    original_filename: Optional[str] = None
    status: Optional[str] = None




############################################################"

class VideoUploadedResponse(BaseModel):
    video_id: UUID
    upload_url: str
    message: str


class VideoUploadRequest(BaseModel):
    filename: str


############################################################

class JobSchema (BaseModel):
    id: UUID
    video_id: UUID
    resolution: Resolution
    s3_output_key: str
    status: JobStatus 
    error_message: Optional[str] = None


class JobCreateSchema(BaseModel):
    id: UUID
    video_id: UUID
    resolution: Resolution
    s3_output_key: str
    status: JobStatus = JobStatus.PENDING
    error_message: Optional[str] = None



class JobUpdateSchema(BaseModel):
    resolution: Optional[Resolution] = None
    s3_output_key: Optional[str] = None
    status: Optional[JobStatus] = None
    error_message: Optional[str] = None


############################################################

class JobChunkCreateSchema(BaseModel):
    id: UUID
    job_id: UUID
    chunk_s3_key: str


class JobChunkUpdateSchema(BaseModel):
    chunk_s3_key: Optional[str] = None







T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[str] = None


class VideoUploadRequest(BaseModel):
    filename: str


class VideoUploadedResponse(BaseModel):
    video_id: UUID
    upload_url: str


class JobSchema(BaseModel):
    id: UUID
    status: str
    # ...other fields


# Specific response types
class UploadResponse(BaseModel):
    video_id: UUID
    upload_url: str


class TranscodeResponse(BaseModel):
    video_id: UUID
    job_id: UUID
    chunks: int


class JobDeleteResponse(BaseModel):
    job_id: UUID