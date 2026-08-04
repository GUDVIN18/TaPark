from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DOCKER_SECRET: str = Field(..., env="DOCKER_SECRET")

    LOG_LEVEL: str = Field("DEBUG")

    QWEN_API_KEY: str = Field(..., env="QWEN_API_KEY")

    MODEL_AI: str = Field(..., env="MODEL_AI")
    ANALYTICS_MODEL_AI: str = Field(..., env="ANALYTICS_MODEL_AI")
    EMBEDDING_MODEL_ID: str = Field(..., env="EMBEDDING_MODEL_ID")

    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASS: str = Field(..., env="POSTGRES_PASS")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_HOST: str = Field(..., env="POSTGRES_HOST")
    DB_MIN_CONNECTIONS: int = Field(1, env="DB_MIN_CONNECTIONS")
    DB_MAX_CONNECTIONS: int = Field(20, env="DB_MAX_CONNECTIONS")


    REDIS_IP: str = Field(..., env="REDIS_IP")
    REDIS_PASS: str = Field(..., env="REDIS_PASS")
    REDIS_PORT: int = Field(..., env="REDIS_PORT")

    QDRANT_HOST: str = Field(..., env="QDRANT_HOST")
    QDRANT_PORT: int = Field(..., env="QDRANT_PORT")
    COLLECTION_NAME_AI: str = Field(..., env="COLLECTION_NAME_AI")
    VECTOR_DIMENSION: int = Field(..., env="VECTOR_DIMENSION")
    BATCH_SIZE: int = Field(..., env="BATCH_SIZE")

    USEDESK_API_TOKEN: str = Field(..., env="USEDESK_API_TOKEN")
    USEDESK_COMPANY_ID: int = Field(..., env="USEDESK_COMPANY_ID")
    USEDESK_CHANNEL_ID: int = Field(..., env="USEDESK_CHANNEL_ID")
    USEDESK_AGENT_ID: int = Field(..., env="USEDESK_AGENT_ID")
    USEDESK_BASE_URL: str = Field(
        "https://api.usedesk.ru",
        env="USEDESK_BASE_URL",
    )
    USEDESK_TIMEOUT_SECONDS: float = Field(
        10.0,
        env="USEDESK_TIMEOUT_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DB_URL() -> str:
        return (
            f"postgresql+asyncpg://{config.POSTGRES_USER}:{config.POSTGRES_PASS}"
            f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
        )
    # @property
    # def DB_MIGRATION_URL() -> str:
    #     return f"postgresql://" \
    #            f"{config.POSTGRES_USER}:{config.POSTGRES_PASS}@" \
    #            f"{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/" \
    #            f"{config.POSTGRES_DB}"

config = Settings()
