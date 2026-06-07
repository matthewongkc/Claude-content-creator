#!/usr/bin/env python3
"""Post one prepared carousel to Instagram — run this on YOUR computer.

Why this exists: the cloud environment that generated your carousel blocks
Instagram's API, so the final publish has to run somewhere that can reach
it — your laptop is perfect. This script has ZERO dependencies (Python 3
standard library only) so you can run it anywhere Python is installed.

What it does:
  1. Reads the prepared post (image URLs + caption) from hosted/<id>/post.json
  2. Uses your access token to find your Instagram Business account id
  3. Builds the carousel and publishes it
  4. Prints the link to the live post

Usage (macOS/Linux):
    IG_ACCESS_TOKEN='EAA...your token...' python3 scripts/post_once.py 1303dc3a4615

Usage (Windows PowerShell):
    $env:IG_ACCESS_TOKEN='EAA...your token...'; python scripts\\post_once.py 1303dc3a4615

If your token has expired (they're short-lived), regenerate it in the Graph
API Explorer and run again.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.facebook.com/v21.0"


def _call(method: str, path: str, params: dict) -> dict:
    url = f"{GRAPH}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"\n✗ {method} {path} failed ({exc.code}):\n{body[:500]}\n")


def get(path: str, params: dict) -> dict:
    return _call("GET", path, params)


def post(path: str, params: dict) -> dict:
    return _call("POST", path, params)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: IG_ACCESS_TOKEN=... python3 scripts/post_once.py <carousel_id>")
    carousel_id = sys.argv[1]
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Set IG_ACCESS_TOKEN in your environment first.")

    manifest_path = Path(__file__).resolve().parent.parent / "hosted" / carousel_id / "post.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    image_urls: list[str] = manifest["image_urls"]
    caption: str = manifest["caption"]

    print(f"Posting {len(image_urls)} slides for carousel {carousel_id}…")

    # 1. Resolve the Instagram Business account id (and its page token).
    accounts = get(
        "me/accounts",
        {
            "fields": "name,access_token,instagram_business_account{id,username}",
            "access_token": token,
        },
    )
    page = next((p for p in accounts.get("data", []) if p.get("instagram_business_account")), None)
    if not page:
        raise SystemExit(
            "No Instagram Business account is linked to a Facebook Page on this token.\n"
            "Make sure @your account is a Business/Creator account linked to a Page,\n"
            "and that the token has instagram_basic + instagram_content_publish + pages_show_list."
        )
    ig_id = page["instagram_business_account"]["id"]
    ig_user = page["instagram_business_account"].get("username", "?")
    page_token = page["access_token"]
    print(f"  → posting to @{ig_user} (ig id {ig_id})")

    # 2. Create one container per slide.
    children = []
    for i, url in enumerate(image_urls, 1):
        c = post(
            f"{ig_id}/media",
            {"image_url": url, "is_carousel_item": "true", "access_token": page_token},
        )
        children.append(c["id"])
        print(f"  → slide {i}/{len(image_urls)} staged")
    time.sleep(5)

    # 3. Create the parent carousel container.
    parent = post(
        f"{ig_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": page_token,
        },
    )
    time.sleep(5)

    # 4. Publish.
    published = post(
        f"{ig_id}/media_publish",
        {"creation_id": parent["id"], "access_token": page_token},
    )
    link = get(published["id"], {"fields": "permalink", "access_token": page_token}).get("permalink")
    print(f"\n✓ Published! {link or published['id']}")


if __name__ == "__main__":
    main()
