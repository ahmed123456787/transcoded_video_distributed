
from src.models import VideoTask, VideoChunk, VideoTrascoded
from src.schema import (
    VideoTaskCreate, VideoTaskUpdate,
    VideoChunkCreate, VideoChunkUpdate,
    VideoTranscodedCreate, VideoTranscodedUpdate
)
from src.services.base_service import BaseService


# Service for the VideoTask model
video_task_service = BaseService[VideoTask, VideoTaskCreate, VideoTaskUpdate](VideoTask)

# Service for the VideoChunk model
video_chunk_service = BaseService[VideoChunk, VideoChunkCreate, VideoChunkUpdate](VideoChunk)

# Service for the VideoTrascoded model
video_transcoded_service = BaseService[VideoTrascoded, VideoTranscodedCreate, VideoTranscodedUpdate](VideoTrascoded)