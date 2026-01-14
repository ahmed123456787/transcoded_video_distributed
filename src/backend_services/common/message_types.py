from dataclasses import dataclass



@dataclass
class ChunkTranscodingMessage:
    video_id: str
    chunk_index: int
    target_format: str
    resolution: str
    bitrate: int