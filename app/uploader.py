"""Make rendered slides reachable by a public URL.

Instagram's Graph API does not accept raw image bytes for feed posts — it
fetches each image from a public `image_url`. So before publishing we host
the PNGs somewhere reachable and hand Instagram the URLs.

Two pluggable backends:
  * imgbb       — free, one API key, simplest to start with.
  * cloudinary  — if you already use it; unsigned-or-signed upload.

Pick one with IMAGE_HOST in your .env.
"""

from __future__ import annotations

import base64
import hashlib
import time
from pathlib import Path

import requests

from .config import Config


class UploadError(RuntimeError):
    pass


def _upload_imgbb(path: Path, api_key: str) -> str:
    with path.open("rb") as fh:
        encoded = base64.b64encode(fh.read()).decode()
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": encoded, "name": path.stem},
        timeout=60,
    )
    if resp.status_code != 200:
        raise UploadError(f"imgbb upload failed ({resp.status_code}): {resp.text[:200]}")
    data = resp.json().get("data", {})
    url = data.get("url") or data.get("display_url")
    if not url:
        raise UploadError(f"imgbb returned no URL: {resp.text[:200]}")
    return url


def _upload_cloudinary(path: Path, cfg: Config) -> str:
    cloud = cfg.secrets.cloudinary_cloud_name
    api_key = cfg.secrets.cloudinary_api_key
    api_secret = cfg.secrets.cloudinary_api_secret
    if not (cloud and api_key and api_secret):
        raise UploadError("Cloudinary credentials are incomplete in .env.")

    timestamp = str(int(time.time()))
    # Signed upload: sha1 of the sorted params + secret.
    to_sign = f"timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(to_sign.encode()).hexdigest()

    with path.open("rb") as fh:
        resp = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
            data={"api_key": api_key, "timestamp": timestamp, "signature": signature},
            files={"file": fh},
            timeout=120,
        )
    if resp.status_code != 200:
        raise UploadError(f"Cloudinary upload failed ({resp.status_code}): {resp.text[:200]}")
    url = resp.json().get("secure_url")
    if not url:
        raise UploadError(f"Cloudinary returned no URL: {resp.text[:200]}")
    return url


def upload_image(path: Path, cfg: Config) -> str:
    """Upload one image and return its public URL."""
    host = (cfg.secrets.image_host or "imgbb").lower()
    if host == "imgbb":
        if not cfg.secrets.imgbb_api_key:
            raise UploadError("IMGBB_API_KEY is not set in .env.")
        return _upload_imgbb(path, cfg.secrets.imgbb_api_key)
    if host == "cloudinary":
        return _upload_cloudinary(path, cfg)
    raise UploadError(f"Unknown IMAGE_HOST '{host}'. Use 'imgbb' or 'cloudinary'.")


def upload_all(paths: list[Path], cfg: Config) -> list[str]:
    return [upload_image(p, cfg) for p in paths]
