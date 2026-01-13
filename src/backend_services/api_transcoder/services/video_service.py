from api_transcoder.models import Video
from api_transcoder.schema import (
    VideoCreateSchema, VideoUpdate
)
from api_transcoder.services.base_service import BaseService


video_service = BaseService[Video, VideoCreateSchema, VideoUpdate](Video)