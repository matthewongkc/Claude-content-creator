"""Make rendered slides reachable by a public URL.

Instagram's Graph API does not accept raw image bytes for feed posts — it
fetches each image from a public `image_url`. So before publishing we host
the PNGs somewhere reachable and hand Instagram the URLs.

Pluggable backends (pick one with IMAGE_HOST in your .env):
  * github      — commit slides to a PUBLIC repo, serve via raw URLs. Free,
                  no extra signup if you already use GitHub.
  * cloudinary  — real CDN, generous free tier; signed upload.
  * imgbb       — free API key, simplest single-key option.
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


GITHUB_API = "https://api.github.com"


def _github_remote_path(path: Path, cfg: Config) -> str:
    """carousels/<carousel-id>/slide_NN.png — groups slides by carousel."""
    prefix = (cfg.secrets.github_image_dir or "carousels").strip("/")
    return f"{prefix}/{path.parent.name}/{path.name}"


def _upload_github(path: Path, cfg: Config) -> str:
    """Commit one image to a public repo via the Contents API; return its raw URL.

    The repo MUST be public — Instagram fetches the raw URL with no auth.
    Re-uploading the same path updates the file in place (idempotent).
    """
    repo = cfg.secrets.github_image_repo
    token = cfg.secrets.github_token
    if not (repo and token and "/" in repo):
        raise UploadError("GITHUB_IMAGE_REPO (owner/repo) and GITHUB_TOKEN must be set.")

    branch = cfg.secrets.github_image_branch or "main"
    remote_path = _github_remote_path(path, cfg)
    url = f"{GITHUB_API}/repos/{repo}/contents/{remote_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # If the file already exists we must pass its blob sha to update it.
    sha = None
    existing = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
    if existing.status_code == 200:
        sha = existing.json().get("sha")

    content_b64 = base64.b64encode(path.read_bytes()).decode()
    payload = {
        "message": f"carousel: add {remote_path}",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201):
        raise UploadError(f"GitHub upload failed ({resp.status_code}): {resp.text[:200]}")

    download_url = resp.json().get("content", {}).get("download_url")
    if not download_url:
        raise UploadError(f"GitHub returned no download_url: {resp.text[:200]}")
    return download_url


def upload_image(path: Path, cfg: Config) -> str:
    """Upload one image and return its public URL."""
    host = (cfg.secrets.image_host or "imgbb").lower()
    if host == "github":
        return _upload_github(path, cfg)
    if host == "imgbb":
        if not cfg.secrets.imgbb_api_key:
            raise UploadError("IMGBB_API_KEY is not set in .env.")
        return _upload_imgbb(path, cfg.secrets.imgbb_api_key)
    if host == "cloudinary":
        return _upload_cloudinary(path, cfg)
    raise UploadError(f"Unknown IMAGE_HOST '{host}'. Use 'github', 'cloudinary', or 'imgbb'.")


def upload_all(paths: list[Path], cfg: Config) -> list[str]:
    return [upload_image(p, cfg) for p in paths]
