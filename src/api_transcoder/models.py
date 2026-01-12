from .database import Base
from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Enum, func, Text
from sqlalchemy.orm import relationship
import enum


# class User(Base):
#     __tablename__ = "users"

#     id = Column(UUID, primary_key=True, index=True)
#     email = Column(String, nullable=False, unique=True, index=True)
#     password_hash = Column(String, nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

#     videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")



class VideoStatus(enum.Enum):
    WAITING_UPLOAD = "WAITING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"



class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID, primary_key=True, index=True)
    # user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    s3_bucket = Column(String, nullable=False)
    presigned_url = Column(Text, nullable=False)
    status = Column(Enum(VideoStatus), nullable=False, default=VideoStatus.WAITING_UPLOAD)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # user = relationship("User", back_populates="videos")
    transcoding_jobs = relationship("TranscodingJob", back_populates="video", cascade="all, delete-orphan")



class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"



class Resolution(enum.Enum):
    R1080P = "1080p"
    R720P = "720p"
    R360P = "360p"



class TranscodingJob(Base):
    __tablename__ = "transcoding_jobs"

    id = Column(UUID, primary_key=True, index=True)
    video_id = Column(UUID, ForeignKey("videos.id"), nullable=False, index=True)
    resolution = Column(Enum(Resolution), nullable=False)
    s3_output_key = Column(String, nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    error_message = Column(Text, nullable=True)

    chunks = relationship("JobChunk", back_populates="job", cascade="all, delete-orphan")
    video = relationship("Video", back_populates="transcoding_jobs")




class JobChunk(Base):
    __tablename__ = "job_chunks"

    id = Column(UUID, primary_key=True, index=True)
    job_id = Column(UUID, ForeignKey("transcoding_jobs.id"), nullable=False, index=True)
    chunk_s3_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    job = relationship("TranscodingJob", back_populates="chunks") 