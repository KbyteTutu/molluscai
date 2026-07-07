from typing import Optional

from pydantic import field_validator, model_validator
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

    # iNaturalist
    INATURALIST_API_KEY: Optional[str] = None

    # MolluscaBase
    MOLLUSCABASE_API_URL: str = "https://api.molluscabase.org"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # App
    APP_NAME: str = "MolluscAI"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/0"

    @field_validator("APP_ENV")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.APP_ENV not in {"production", "prod"}:
            return self

        weak_values = {
            "POSTGRES_PASSWORD": "mollusc_dev",
            "MINIO_ACCESS_KEY": "minioadmin",
            "MINIO_SECRET_KEY": "minioadmin",
            "JWT_SECRET_KEY": "replace-me-with-a-secure-random-secret",
            "JWT_REFRESH_SECRET_KEY": "replace-me-with-another-secure-secret",
            "ENCRYPTION_KEY": "replace-me-with-a-32-byte-hex-key",
        }
        configured = {
            "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
            "MINIO_ACCESS_KEY": self.MINIO_ACCESS_KEY,
            "MINIO_SECRET_KEY": self.MINIO_SECRET_KEY,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
            "JWT_REFRESH_SECRET_KEY": self.JWT_REFRESH_SECRET_KEY,
            "ENCRYPTION_KEY": self.ENCRYPTION_KEY,
        }
        unsafe = [name for name, weak in weak_values.items() if configured[name] == weak]
        invalid = [
            name
            for name in ("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY")
            if len(configured[name]) < 32
        ]
        if len(self.ENCRYPTION_KEY) != 64:
            invalid.append("ENCRYPTION_KEY")
        else:
            try:
                bytes.fromhex(self.ENCRYPTION_KEY)
            except ValueError:
                invalid.append("ENCRYPTION_KEY")

        failures = sorted(set(unsafe + invalid))
        if failures:
            raise ValueError(
                "Refusing to start in production with weak or invalid secret settings: "
                + ", ".join(failures)
            )
        return self


settings = Settings()
