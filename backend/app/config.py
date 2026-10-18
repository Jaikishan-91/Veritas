from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERITAS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/veritas.db"
    storage_backend: str = "local"  # local | minio
    local_storage_dir: str = "./data/objects"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "veritas"
    minio_secure: bool = False

    max_upload_mb: int = 25
    max_pages: int = 20
    render_dpi: int = 150
    workers: int = 2

    # Fusion / routing
    band_medium: float = 0.3
    band_high: float = 0.6
    review_low: float = 0.3
    review_high: float = 0.7
    min_coverage: float = 0.75

    cors_origins: str = "http://localhost:5173,http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
