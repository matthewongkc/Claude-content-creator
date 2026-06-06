"""Persistence — a dead-simple JSON store under content/.

Each carousel lives in content/<id>/ with:
  * carousel.json   — the record
  * slide_01.png …  — rendered images

This is intentionally file-based: no database to set up, everything is
inspectable, and you can copy a carousel folder anywhere. For a single
creator posting a few times a day, this is plenty.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import CONTENT_DIR
from .models import Carousel, Status


def carousel_dir(carousel_id: str) -> Path:
    return CONTENT_DIR / carousel_id


def _record_path(carousel_id: str) -> Path:
    return carousel_dir(carousel_id) / "carousel.json"


def save(carousel: Carousel) -> None:
    carousel.touch()
    d = carousel_dir(carousel.id)
    d.mkdir(parents=True, exist_ok=True)
    _record_path(carousel.id).write_text(json.dumps(carousel.to_dict(), indent=2))


def load(carousel_id: str) -> Carousel | None:
    path = _record_path(carousel_id)
    if not path.exists():
        return None
    return Carousel.from_dict(json.loads(path.read_text()))


def list_all() -> list[Carousel]:
    """All carousels, newest first."""
    items: list[Carousel] = []
    if not CONTENT_DIR.exists():
        return items
    for child in CONTENT_DIR.iterdir():
        record = child / "carousel.json"
        if record.exists():
            try:
                items.append(Carousel.from_dict(json.loads(record.read_text())))
            except (json.JSONDecodeError, KeyError):
                continue
    items.sort(key=lambda c: c.created_at, reverse=True)
    return items


def list_by_status(status: Status) -> list[Carousel]:
    return [c for c in list_all() if c.status == status]
