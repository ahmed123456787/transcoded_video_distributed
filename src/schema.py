from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class VideoUploadResponse(BaseModel):
    message: str
    video_id: str


class VideoTaskBase(BaseModel):
    input_file: str
    output_file: str
    status: Optional[str] = None


class VideoTaskCreate(VideoTaskBase):
    id: UUID


class VideoTaskUpdate(BaseModel):
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    status: Optional[str] = None


class VideoChunkBase(BaseModel):
    video_task_id: UUID
    chunk_file: str
    status: Optional[str] = None


class VideoChunkCreate(VideoChunkBase):
    id: UUID


class VideoChunkUpdate(BaseModel):
    video_task_id: Optional[UUID] = None
    chunk_file: Optional[str] = None
    status: Optional[str] = None


class VideoTranscodedBase(BaseModel):
    video_task_id: UUID
    transcoded_file: str
    status: Optional[str] = None


class VideoTranscodedCreate(VideoTranscodedBase):
    id: UUID
    

class VideoTranscodedUpdate(BaseModel):
    video_task_id: Optional[UUID] = None
    transcoded_file: Optional[str] = None
    status: Optional[str] = None