from dataclasses import dataclass



@dataclass
class ChunkTranscodingMessage:
    id: str
    job_id: str
    chunk_index: int
    target_format: str
    resolution: str
    bitrate: int
    chunk_s3_key: str