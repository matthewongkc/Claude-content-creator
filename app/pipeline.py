"""Orchestration: the steps that move a carousel through its lifecycle.

  generate_and_render()  → draft copy + render slides → save as PENDING
  rerender()             → re-render after you edit copy / change theme
  publish()              → host images + post to Instagram → mark PUBLISHED

The dashboard and the daily script both call into here, so the rules live
in one place.
"""

from __future__ import annotations

from . import generator, instagram, store, uploader
from .config import Config
from .models import Carousel, CarouselContent, Status
from .renderer import render_carousel
from .store import carousel_dir


def generate_and_render(config: Config, topic: str | None = None) -> Carousel:
    """Draft a new carousel with Claude and render its slides."""
    content = generator.generate(config, topic)
    carousel = Carousel.new(content, theme=config.brand.theme)
    carousel.status = Status.PENDING
    store.save(carousel)
    rerender(config, carousel)
    return carousel


def create_from_content(config: Config, content: CarouselContent, theme: str | None = None) -> Carousel:
    """Create a carousel from copy you supplied yourself (no Claude call)."""
    carousel = Carousel.new(content, theme=theme or config.brand.theme)
    carousel.status = Status.PENDING
    store.save(carousel)
    rerender(config, carousel)
    return carousel


def rerender(config: Config, carousel: Carousel) -> Carousel:
    """(Re)render slide images for a carousel and persist the paths."""
    out_dir = carousel_dir(carousel.id)
    paths = render_carousel(carousel, out_dir, handle=config.brand.handle)
    carousel.image_paths = [str(p.relative_to(carousel_dir(carousel.id).parent)) for p in paths]
    store.save(carousel)
    return carousel


def dry_run_publish(config: Config, carousel: Carousel) -> list[str]:
    """Rehearse publishing: host the images and return their public URLs, but
    do NOT post to Instagram. Lets you validate image hosting end-to-end and
    eyeball the exact URLs Instagram would receive."""
    base = carousel_dir(carousel.id).parent
    paths = [base / rel for rel in carousel.image_paths]
    if not paths:
        raise RuntimeError("No rendered images found — re-render the carousel first.")
    return uploader.upload_all(paths, config)


def publish(config: Config, carousel: Carousel) -> Carousel:
    """Host the rendered images and post the carousel to Instagram.

    Refuses to publish unless the carousel is APPROVED (when approval is
    required) and publishing is enabled — you stay the gatekeeper.
    """
    if config.publishing.require_approval and carousel.status != Status.APPROVED:
        raise RuntimeError(
            "Carousel must be APPROVED before publishing. Approve it in the dashboard first."
        )
    if not config.can_publish:
        raise RuntimeError(
            "Publishing is disabled or Instagram credentials are missing. "
            "Set auto_post_enabled: true and configure IG_* in .env."
        )

    base = carousel_dir(carousel.id).parent
    paths = [base / rel for rel in carousel.image_paths]
    if not paths:
        raise RuntimeError("No rendered images found — re-render the carousel first.")

    try:
        urls = uploader.upload_all(paths, config)
        permalink = instagram.publish_carousel(
            config, urls, carousel.content.caption_with_tags()
        )
        carousel.status = Status.PUBLISHED
        carousel.instagram_permalink = permalink
        carousel.error = None
    except Exception as exc:  # noqa: BLE001 — surface any failure to the user
        carousel.status = Status.FAILED
        carousel.error = str(exc)
        store.save(carousel)
        raise

    store.save(carousel)
    return carousel
