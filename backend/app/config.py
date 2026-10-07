from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./ncep.db"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    demo_password: str = "password"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    ecg_storage_root: str = "./data/ecg_storage"
    ecg_upload_temp_dir: str = "./data/ecg_uploads"
    ecg_upload_status_dir: str = "./data/ecg_upload_status"
    report_storage_root: str = "./data/report_storage"

    # Durability backup for the two artifact stores above (app/storage/cloudinary_backup.py).
    # Local disk stays the fast path everywhere; Cloudinary is only read from
    # when a file is missing locally (a different instance, or disk wiped by
    # a restart/redeploy on a host with no persistent volume). Left blank,
    # the stores behave exactly as local-disk-only, as before this existed.
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Canonical ECG artifacts must outlive the process that created them.
    # ``auto`` selects Cloudinary in production and a filesystem-backed test
    # store elsewhere. A production deployment with a genuinely persistent
    # mounted volume may explicitly select ``filesystem``.
    ecg_durable_storage_mode: str = "auto"
    artifact_download_timeout_seconds: float = 15.0
    report_context_timeout_seconds: float = 45.0
    report_stale_after_seconds: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_ecg_durable_storage_mode(self) -> str:
        mode = self.ecg_durable_storage_mode.strip().lower()
        if mode == "auto":
            return "cloudinary" if self.app_env == "production" else "filesystem"
        if mode not in {"cloudinary", "filesystem"}:
            raise ValueError("ecg_durable_storage_mode must be auto, cloudinary, or filesystem")
        return mode

    @model_validator(mode="after")
    def _reject_default_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError(
                "jwt_secret must be set to a real secret when app_env=production "
                "(refusing to sign tokens with the public default value)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
