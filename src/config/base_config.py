from pydantic_settings import BaseSettings
from pydantic import Field

class BaseConfig(BaseSettings):

    MINIO_ENDPOINT: str = Field(..., env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field(..., env="MINIO_BUCKET")
    KAFKA_BROKER: str = Field(..., env="KAFKA_BROKER")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
    