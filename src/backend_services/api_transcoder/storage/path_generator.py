import uuid
from enum import Enum


class StoragePaths(str, Enum):
    RAW = "raw"
    CHUNKS = "chunks"
    TRANSCODED = "transcoded"


def generate_object_name(extension: str, prefix: str = StoragePaths.RAW) -> str:
    id = str(uuid.uuid4())
    return f"{prefix}/{id}.{extension}"



def generate_raw_object_name(extension: str) -> str:
    return f"{StoragePaths.RAW}/{uuid.uuid4()}.{extension}"


def generate_chunk_object_name(video_id: str, chunk_index: int, extension: str = "mp4") -> str:
    return f"{StoragePaths.CHUNKS}/{video_id}/chunk_{chunk_index:03d}.{extension}"


def generate_transcoded_object_name(video_id: str, quality: str, extension: str = "mp4") -> str:
    return f"{StoragePaths.TRANSCODED}/{video_id}/{quality}.{extension}"