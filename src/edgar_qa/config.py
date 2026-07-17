from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    sec_user_agent: str = Field(default="")
    sec_requests_per_second: float = Field(default=8.0, gt=0, le=10)
    sec_timeout_seconds: float = Field(default=30.0, gt=0)
    data_dir: Path = Path("data")

    @field_validator("sec_user_agent")
    @classmethod
    def validate_sec_user_agent(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(
                "SEC_USER_AGENT is required. Use 'Your Name your.email@example.com'."
            )
        if "@" not in cleaned:
            raise ValueError("SEC_USER_AGENT must include a contact email address.")
        return cleaned


def get_settings() -> Settings:
    return Settings()
