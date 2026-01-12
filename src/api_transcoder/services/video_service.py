from src.api_transcoder.models import Video
from src.api_transcoder.schema import (
    VideoCreateSchema, VideoUpdate
)
from src.api_transcoder.services.base_service import BaseService


# Service for the VideoTask model
video_service = BaseService[Video, VideoCreateSchema, VideoUpdate](Video)