from pydantic import BaseModel
from typing import Optional
from uuid import UUID


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