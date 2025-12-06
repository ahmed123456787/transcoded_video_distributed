import enum
import dataclasses


class EventType(enum.Enum):
    VIDEO_UPLOADED = "video_uploaded"
    VIDEO_CHUNKED = "video_chunked"
    VIDEO_TRANSCODED = "video_transcoded"
    VIDEO_FAILED = "video_failed"


@dataclasses.dataclass
class Event:
    event_type: EventType
    payload: dict