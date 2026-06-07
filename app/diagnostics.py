"""Health checks for each integration.

`python run.py doctor` runs these so you can confirm your credentials work
*before* you rely on them — and crucially, **without posting anything** to
Instagram. Each check is read-only or self-cleaning.

Returns structured results the CLI and the dashboard status page both use.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO

import requests

from .config import Config
from .instagram import GRAPH


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str

    @property
    def icon(self) -> str:
        return "✓" if self.ok else "✗"


def check_claude(cfg: Config) -> CheckResult:
    """Verify the Anthropic key with a free token-count call (no generation)."""
    if not cfg.secrets.anthropic_api_key:
        return CheckResult("Claude (Anthropic)", False, "ANTHROPIC_API_KEY not set")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=cfg.secrets.anthropic_api_key)
        client.messages.count_tokens(
            model=cfg.content.model,
            messages=[{"role": "user", "content": "ping"}],
        )
        return CheckResult("Claude (Anthropic)", True, f"key valid · model {cfg.content.model}")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Claude (Anthropic)", False, str(exc)[:160])


def check_image_host(cfg: Config) -> CheckResult:
    """Verify the configured image host. Read-only / self-cleaning per backend."""
    host = (cfg.secrets.image_host or "imgbb").lower()
    if host == "github":
        repo = cfg.secrets.github_image_repo
        token = cfg.secrets.github_token
        if not (repo and token and "/" in repo):
            return CheckResult(
                "Image host (github)", False, "set GITHUB_IMAGE_REPO (owner/repo) + GITHUB_TOKEN"
            )
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return CheckResult("Image host (github)", False, f"{resp.status_code}: {resp.text[:120]}")
            data = resp.json()
            if data.get("private", True):
                return CheckResult(
                    "Image host (github)", False,
                    f"{repo} is private — Instagram can't fetch raw URLs. Make it public.",
                )
            if not data.get("permissions", {}).get("push", False):
                return CheckResult(
                    "Image host (github)", False, f"token lacks push access to {repo}"
                )
            return CheckResult("Image host (github)", True, f"{repo} public + writable")
        except Exception as exc:  # noqa: BLE001
            return CheckResult("Image host (github)", False, str(exc)[:160])
    if host == "imgbb":
        if not cfg.secrets.imgbb_api_key:
            return CheckResult("Image host (imgbb)", False, "IMGBB_API_KEY not set")
        try:
            # Smallest valid PNG, base64-encoded.
            png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            )
            encoded = base64.b64encode(png).decode()
            resp = requests.post(
                "https://api.imgbb.com/1/upload",
                data={
                    "key": cfg.secrets.imgbb_api_key,
                    "image": encoded,
                    "expiration": "60",  # auto-delete the probe image
                    "name": "carousel-studio-healthcheck",
                },
                timeout=30,
            )
            if resp.status_code == 200 and resp.json().get("data", {}).get("url"):
                return CheckResult("Image host (imgbb)", True, "upload OK (probe auto-expires)")
            return CheckResult("Image host (imgbb)", False, f"{resp.status_code}: {resp.text[:120]}")
        except Exception as exc:  # noqa: BLE001
            return CheckResult("Image host (imgbb)", False, str(exc)[:160])
    if host == "cloudinary":
        have = all(
            (
                cfg.secrets.cloudinary_cloud_name,
                cfg.secrets.cloudinary_api_key,
                cfg.secrets.cloudinary_api_secret,
            )
        )
        detail = "credentials present" if have else "missing CLOUDINARY_* values"
        return CheckResult("Image host (cloudinary)", have, detail)
    return CheckResult(f"Image host ({host})", False, "unknown IMAGE_HOST")


def check_instagram(cfg: Config) -> CheckResult:
    """Read-only: fetch account info to confirm the token + user id work."""
    if not (cfg.secrets.ig_user_id and cfg.secrets.ig_access_token):
        return CheckResult("Instagram (Graph API)", False, "IG_USER_ID / IG_ACCESS_TOKEN not set")
    try:
        resp = requests.get(
            f"{GRAPH}/{cfg.secrets.ig_user_id}",
            params={
                "fields": "username,account_type",
                "access_token": cfg.secrets.ig_access_token,
            },
            timeout=30,
        )
        data = resp.json()
        if resp.status_code != 200 or "error" in data:
            msg = data.get("error", {}).get("message", resp.text[:160])
            return CheckResult("Instagram (Graph API)", False, msg)
        username = data.get("username", "?")
        acct = data.get("account_type", "?")
        ok = acct in ("BUSINESS", "CREATOR", "MEDIA_CREATOR")
        note = "" if ok else " — needs a Business/Creator account to publish"
        return CheckResult("Instagram (Graph API)", ok, f"@{username} ({acct}){note}")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Instagram (Graph API)", False, str(exc)[:160])


def run_all(cfg: Config) -> list[CheckResult]:
    return [check_claude(cfg), check_image_host(cfg), check_instagram(cfg)]
