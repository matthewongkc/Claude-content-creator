"""Data models for carousels.

Two layers:
  * Pydantic models (Slide, CarouselContent) — the structured output we
    ask Claude to produce, and that you edit in the dashboard.
  * Carousel — the persisted record wrapping that content with status,
    timestamps, file paths, and publish metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    """Lifecycle of a carousel. You move it from PENDING → APPROVED."""

    DRAFT = "draft"          # generated, not yet rendered
    PENDING = "pending"      # rendered, awaiting your review
    APPROVED = "approved"    # you greenlit it; eligible to publish
    REJECTED = "rejected"    # you killed it
    PUBLISHED = "published"  # live on Instagram
    FAILED = "failed"        # a publish attempt errored


class Slide(BaseModel):
    """One carousel slide.

    `kind` is one of: cover (slide 1 hook), point (a content slide),
    cta (closing call-to-action). The renderer styles each differently.
    """

    kind: str = Field(description="One of: cover, point, cta")
    title: str = Field(description="Large headline text for the slide")
    body: str = Field(default="", description="Optional supporting line(s)")


class CarouselContent(BaseModel):
    """The editable copy of a carousel — what Claude drafts and you tweak."""

    topic: str = Field(description="The subject, e.g. 'motivational' or a custom prompt")
    slides: list[Slide] = Field(description="Ordered slides: cover, points…, cta")
    caption: str = Field(description="Instagram caption (no hashtags)")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags without the # sign")

    def caption_with_tags(self) -> str:
        tags = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
        return f"{self.caption}\n\n{tags}".strip()


@dataclass
class Carousel:
    """A persisted carousel record."""

    id: str
    content: CarouselContent
    theme: str
    status: Status = Status.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    image_paths: list[str] = field(default_factory=list)
    cover_image: str | None = None  # filename of the cover photo inside the carousel dir
    instagram_permalink: str | None = None
    error: str | None = None

    @staticmethod
    def new(content: CarouselContent, theme: str) -> "Carousel":
        return Carousel(id=uuid.uuid4().hex[:12], content=content, theme=theme)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ---- serialization ------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d["content"] = self.content.model_dump()
        d["status"] = self.status.value
        return d

    @staticmethod
    def from_dict(d: dict) -> "Carousel":
        return Carousel(
            id=d["id"],
            content=CarouselContent(**d["content"]),
            theme=d.get("theme", "midnight"),
            status=Status(d.get("status", "pending")),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=d.get("updated_at", datetime.now(timezone.utc).isoformat()),
            image_paths=d.get("image_paths", []),
            cover_image=d.get("cover_image"),
            instagram_permalink=d.get("instagram_permalink"),
            error=d.get("error"),
        )
