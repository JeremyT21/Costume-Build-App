"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the Cospal backend."""

    model: str = os.getenv("COSPAL_MODEL", "")
    amazon_provider: str = os.getenv("AMAZON_PROVIDER", "").lower()
    rainforest_api_key: str = os.getenv("RAINFOREST_API_KEY", "")
    amazon_domain: str = os.getenv("AMAZON_DOMAIN", "amazon.com")
    amazon_associate_tag: str = os.getenv("AMAZON_ASSOCIATE_TAG", "")
    data_dir: Path = Path(os.getenv("COSPAL_DATA_DIR", str(BACKEND_DIR / "data")))
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
    )

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'cospal.db'}"

    @property
    def llm_enabled(self) -> bool:
        """True when a model is configured and offline mode is off."""
        return bool(self.model) and os.getenv("COSPAL_OFFLINE") != "1"


settings = Settings()
