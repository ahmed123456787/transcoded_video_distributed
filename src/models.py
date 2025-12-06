from .database import Base
from sqlalchemy import Column, Integer, String, UUID, ForeignKey
from events.event import EventType



class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(UUID, primary_key=True, index=True)
    input_file = Column(String, nullable=False)
    output_file = Column(String, nullable=False)
    status = Column(String, default=EventType.VIDEO_UPLOADED.value)


class VideoChunk(Base):
    __tablename__ = "video_chunks"
    
    id = Column(UUID, primary_key=True, index=True)
    video_task_id = Column(UUID, ForeignKey("video_tasks.id"), nullable=False)
    chunk_file = Column(String, nullable=False)
    status = Column(String, default=EventType.VIDEO_CHUNKED.value)


class VideoTrascoded(Base): 
    __tablename__ = "video_transcoded"
    
    id = Column(UUID, primary_key=True, index=True)
    video_task_id = Column(UUID, ForeignKey("video_tasks.id"), nullable=False)
    transcoded_file = Column(String, nullable=False)
    status = Column(String, default=EventType.VIDEO_TRANSCODED.value)
