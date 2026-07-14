from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DOCKER_SECRET: str = Field(..., env="DOCKER_SECRET")

    LOG_LEVEL: str = Field("DEBUG")

    QWEN_API_KEY: str = Field(..., env="QWEN_API_KEY")

    MODEL_AI: str = Field(..., env="MODEL_AI")
    ANALYTICS_MODEL_AI: str = Field(..., env="ANALYTICS_MODEL_AI")
    EMBEDDING_MODEL_ID: str = Field(..., env="EMBEDDING_MODEL_ID")

    REDIS_IP: str = Field(..., env="REDIS_IP")
    REDIS_PASS: str = Field(..., env="REDIS_PASS")
    REDIS_PORT: int = Field(..., env="REDIS_PORT")

    QDRANT_HOST: str = Field(..., env="QDRANT_HOST")
    QDRANT_PORT: int = Field(..., env="QDRANT_PORT")
    COLLECTION_NAME_AI: str = Field(..., env="COLLECTION_NAME_AI")
    VECTOR_DIMENSION: int = Field(..., env="VECTOR_DIMENSION")
    BATCH_SIZE: int = Field(..., env="BATCH_SIZE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config = Settings()