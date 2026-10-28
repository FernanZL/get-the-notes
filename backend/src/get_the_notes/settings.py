from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GTN_")

    data_dir: Path = Path("data")
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "gtn"
    max_upload_mb: int = 100
    max_duration_s: float = 15 * 60
    job_timeout_s: int = 2 * 60 * 60
    result_ttl_s: int = 7 * 24 * 60 * 60

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


settings = Settings()
