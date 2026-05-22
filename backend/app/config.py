from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL
    POSTGRES_USER: str = "mollusc"
    POSTGRES_PASSWORD: str = "mollusc_dev"
    POSTGRES_DB: str = "molluscai"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9002"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "molluscai"

    # JWT
    JWT_SECRET_KEY: str = "replace-me-with-a-secure-random-secret"
    JWT_REFRESH_SECRET_KEY: str = "replace-me-with-another-secure-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption (for model API keys in DB)
    ENCRYPTION_KEY: str = "replace-me-with-a-32-byte-hex-key"

    # External API Keys
    DEEPSEEK_API_KEY: Optional[str] = None
    SILICONFLOW_API_KEY: Optional[str] = None
    ZHIPU_API_KEY: Optional[str] = None

    # MolluscaBase
    MOLLUSCABASE_API_URL: str = "https://api.molluscabase.org"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # App
    APP_NAME: str = "MolluscAI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/0"


settings = Settings()
