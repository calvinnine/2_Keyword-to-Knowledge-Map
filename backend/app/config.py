from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "changeme"

    database_url: str = "postgresql+psycopg2://k2km:k2km@localhost:5432/k2km"
    database_url_async: str = "postgresql+asyncpg://k2km:k2km@localhost:5432/k2km"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    openalex_email: str = ""
    openalex_api_key: str = ""

    semantic_scholar_api_key: str = ""

    job_default_max_papers: int = 20_000
    job_absolute_max_papers: int = 50_000


settings = Settings()
