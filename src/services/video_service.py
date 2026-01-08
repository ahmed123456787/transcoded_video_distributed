from src.models import Video, TranscodingJob
from src.schema import (
    VideoCreateSchema, VideoUpdate
)
from src.services.base_service import BaseService


# Service for the VideoTask model
video_task_service = BaseService[Video, VideoCreateSchema, VideoUpdate](Video)