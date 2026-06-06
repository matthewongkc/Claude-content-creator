"""Configuration loading.

Settings come from two places:
  * config.yaml      — non-secret preferences (brand, themes, schedule)
  * .env / env vars  — secrets (API keys, tokens)

Both are optional at import time; we fall back to sane defaults and a
bundled example so the app can at least render local previews without
any credentials.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root = parent of this file's package directory.
ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
FONTS_DIR = ROOT / "assets" / "fonts"

load_dotenv(ROOT / ".env")


def _load_yaml() -> dict:
    """Load config.yaml, falling back to config.example.yaml."""
    for name in ("config.yaml", "config.example.yaml"):
        path = ROOT / name
        if path.exists():
            with path.open() as fh:
                return yaml.safe_load(fh) or {}
    return {}


@dataclass
class BrandConfig:
    handle: str = "@yourbrand"
    theme: str = "midnight"


@dataclass
class ContentConfig:
    topics: list[str] = field(default_factory=lambda: ["motivational", "parenting"])
    slides_per_carousel: int = 7
    model: str = "claude-opus-4-8"

    def pick_topic(self) -> str:
        """Weighted random topic (duplicates in the list raise the odds)."""
        return random.choice(self.topics) if self.topics else "motivational"


@dataclass
class PublishingConfig:
    auto_post_enabled: bool = False
    require_approval: bool = True


@dataclass
class Secrets:
    anthropic_api_key: str | None = None
    ig_user_id: str | None = None
    ig_access_token: str | None = None
    image_host: str = "imgbb"
    imgbb_api_key: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    dashboard_secret: str = "dev-secret-change-me"


@dataclass
class Config:
    brand: BrandConfig
    content: ContentConfig
    publishing: PublishingConfig
    secrets: Secrets

    @property
    def can_generate(self) -> bool:
        return bool(self.secrets.anthropic_api_key)

    @property
    def can_publish(self) -> bool:
        return bool(
            self.publishing.auto_post_enabled
            and self.secrets.ig_user_id
            and self.secrets.ig_access_token
        )


def load_config() -> Config:
    data = _load_yaml()

    brand = BrandConfig(**{**BrandConfig().__dict__, **(data.get("brand") or {})})

    content_raw = data.get("content") or {}
    content = ContentConfig(
        topics=content_raw.get("topics") or ContentConfig().topics,
        slides_per_carousel=int(
            content_raw.get("slides_per_carousel", ContentConfig().slides_per_carousel)
        ),
        model=content_raw.get("model", ContentConfig().model),
    )

    pub_raw = data.get("publishing") or {}
    publishing = PublishingConfig(
        auto_post_enabled=bool(pub_raw.get("auto_post_enabled", False)),
        require_approval=bool(pub_raw.get("require_approval", True)),
    )

    secrets = Secrets(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        ig_user_id=os.getenv("IG_USER_ID"),
        ig_access_token=os.getenv("IG_ACCESS_TOKEN"),
        image_host=os.getenv("IMAGE_HOST", "imgbb"),
        imgbb_api_key=os.getenv("IMGBB_API_KEY"),
        cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY"),
        cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        dashboard_secret=os.getenv("DASHBOARD_SECRET", "dev-secret-change-me"),
    )

    CONTENT_DIR.mkdir(exist_ok=True)
    return Config(brand=brand, content=content, publishing=publishing, secrets=secrets)
