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
    workers: int = 1  # PyMuPDF is not thread-safe; scale with processes/replicas (ADR-002)
    max_image_pixels: int = 60_000_000
    max_render_side: int = 4000

    # Fusion / routing
    band_medium: float = 0.3
    band_high: float = 0.6
    review_low: float = 0.3
    review_high: float = 0.7
    min_coverage: float = 0.75

    # Auth
    session_hours: int = 12
    cookie_secure: bool = False  # set true behind HTTPS
    bootstrap_admin_email: str = ""  # created on startup if no users exist
    bootstrap_admin_password: str = ""

    secret_key: str = ""  # HMAC key for OTP hashes; random per process if unset (codes die on restart)
    allow_signup: bool = True
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_seconds: int = 60

    # Outgoing mail for OTP codes. Empty smtp_host = log codes to the console (development only).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_security: str = "starttls"  # starttls | ssl | none

    cors_origins: str = "http://localhost:5173,http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
