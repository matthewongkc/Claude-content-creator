"""Offline tests — no network, no API keys.

These cover the parts that must never silently break: the model
round-trips through JSON, the store reads what it writes, the renderer
produces real PNGs at the right size, and the dashboard serves its pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store  # noqa: E402
from app.config import load_config  # noqa: E402
from app.models import Carousel, CarouselContent, Slide, Status  # noqa: E402
from app.renderer import HEIGHT, WIDTH, render_carousel  # noqa: E402


def _sample_content() -> CarouselContent:
    return CarouselContent(
        topic="motivational",
        slides=[
            Slide(kind="cover", title="Start before you feel ready"),
            Slide(kind="point", title="Motivation follows action", body="Move first."),
            Slide(kind="cta", title="Do one tiny thing today", body="Save this."),
        ],
        caption="A short caption.",
        hashtags=["motivation", "discipline"],
    )


def test_caption_with_tags():
    content = _sample_content()
    out = content.caption_with_tags()
    assert "#motivation" in out and "#discipline" in out
    assert out.startswith("A short caption.")


def test_carousel_roundtrip():
    c = Carousel.new(_sample_content(), theme="forest")
    restored = Carousel.from_dict(c.to_dict())
    assert restored.id == c.id
    assert restored.theme == "forest"
    assert restored.status == Status.PENDING
    assert len(restored.content.slides) == 3
    assert restored.content.slides[0].kind == "cover"


def test_store_save_and_load(tmp_path, monkeypatch):
    # Redirect the content dir to a temp location for isolation.
    monkeypatch.setattr(store, "CONTENT_DIR", tmp_path)
    c = Carousel.new(_sample_content(), theme="ocean")
    store.save(c)
    loaded = store.load(c.id)
    assert loaded is not None
    assert loaded.content.topic == "motivational"
    assert c.id in [x.id for x in store.list_all()]


def test_renderer_outputs_pngs(tmp_path):
    config = load_config()
    c = Carousel.new(_sample_content(), theme="midnight")
    paths = render_carousel(c, tmp_path, handle=config.brand.handle)
    assert len(paths) == 3
    for p in paths:
        assert p.exists()
        with Image.open(p) as img:
            assert img.size == (WIDTH, HEIGHT)


def test_renderer_handles_long_text(tmp_path):
    # Very long title must still fit (auto-shrink) without crashing.
    content = CarouselContent(
        topic="parenting",
        slides=[
            Slide(kind="cover", title="A" * 120),
            Slide(kind="point", title="word " * 40, body="lorem ipsum " * 30),
            Slide(kind="cta", title="Go"),
        ],
        caption="x",
        hashtags=[],
    )
    c = Carousel.new(content, theme="plum")
    paths = render_carousel(c, tmp_path, handle="@test")
    assert all(p.exists() for p in paths)


@pytest.mark.parametrize("theme", ["midnight", "sunrise", "forest", "plum", "mono", "ocean", "ember"])
def test_all_themes_render(tmp_path, theme):
    c = Carousel.new(_sample_content(), theme=theme)
    paths = render_carousel(c, tmp_path / theme, handle="@t")
    assert len(paths) == 3


def test_dashboard_pages(tmp_path, monkeypatch):
    import app.dashboard as dash
    import app.config as cfg

    monkeypatch.setattr(cfg, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(store, "CONTENT_DIR", tmp_path)

    application = dash.create_app()
    client = application.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/status").status_code == 200

    c = Carousel.new(_sample_content(), theme="mono")
    render_carousel(c, tmp_path / c.id, handle="@t")
    c.image_paths = [f"{c.id}/slide_{i:02d}.png" for i in (1, 2, 3)]
    store.save(c)

    assert client.get(f"/carousel/{c.id}").status_code == 200
    assert client.get("/carousel/does-not-exist").status_code == 404
