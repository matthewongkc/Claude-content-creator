"""Publish a carousel to Instagram via the official Graph API.

The carousel ("CAROUSEL_ALBUM") flow has three steps:
  1. Create an image container per slide        (media, is_carousel_item)
  2. Create the parent carousel container        (media_type=CAROUSEL)
  3. Publish the parent container                (media_publish)

Requirements (see README for setup):
  * Instagram Business/Creator account linked to a Facebook Page
  * A Meta app + long-lived access token with instagram_content_publish
  * IG_USER_ID and IG_ACCESS_TOKEN in .env

Each slide image must already be at a public URL (see uploader.py).
"""

from __future__ import annotations

import time

import requests

from .config import Config

GRAPH = "https://graph.facebook.com/v21.0"


class InstagramError(RuntimeError):
    pass


def _post(url: str, params: dict) -> dict:
    resp = requests.post(url, data=params, timeout=60)
    payload = resp.json() if resp.content else {}
    if resp.status_code != 200 or "error" in payload:
        msg = payload.get("error", {}).get("message", resp.text[:300])
        raise InstagramError(f"Graph API error ({resp.status_code}): {msg}")
    return payload


def _create_item_container(cfg: Config, image_url: str) -> str:
    data = _post(
        f"{GRAPH}/{cfg.secrets.ig_user_id}/media",
        {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": cfg.secrets.ig_access_token,
        },
    )
    return data["id"]


def _create_carousel_container(cfg: Config, children: list[str], caption: str) -> str:
    data = _post(
        f"{GRAPH}/{cfg.secrets.ig_user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": cfg.secrets.ig_access_token,
        },
    )
    return data["id"]


def _publish(cfg: Config, creation_id: str) -> str:
    data = _post(
        f"{GRAPH}/{cfg.secrets.ig_user_id}/media_publish",
        {"creation_id": creation_id, "access_token": cfg.secrets.ig_access_token},
    )
    return data["id"]


def _permalink(cfg: Config, media_id: str) -> str | None:
    try:
        resp = requests.get(
            f"{GRAPH}/{media_id}",
            params={"fields": "permalink", "access_token": cfg.secrets.ig_access_token},
            timeout=30,
        )
        return resp.json().get("permalink")
    except (requests.RequestException, ValueError):
        return None


def publish_carousel(cfg: Config, image_urls: list[str], caption: str) -> str:
    """Publish a carousel and return its permalink (or media id)."""
    if not (cfg.secrets.ig_user_id and cfg.secrets.ig_access_token):
        raise InstagramError("IG_USER_ID / IG_ACCESS_TOKEN are not configured.")
    if not 2 <= len(image_urls) <= 10:
        raise InstagramError(
            f"A carousel needs 2-10 images; got {len(image_urls)}."
        )

    children = [_create_item_container(cfg, url) for url in image_urls]

    # Containers can take a moment to be processed before they're usable.
    time.sleep(5)

    parent = _create_carousel_container(cfg, children, caption)
    time.sleep(5)

    media_id = _publish(cfg, parent)
    return _permalink(cfg, media_id) or media_id
