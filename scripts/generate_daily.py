#!/usr/bin/env python3
"""Generate the day's carousel draft(s).

Run this from cron or a CI scheduler. It only *drafts* — it never posts.
You review and approve in the dashboard (or with `run.py publish`), keeping
you firmly in the loop.

Example crontab (8am daily):
  0 8 * * *  cd /path/to/Claude-content-creator && /usr/bin/python3 scripts/generate_daily.py

Or GitHub Actions: see README → "Scheduling".
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import pipeline  # noqa: E402
from app.config import load_config  # noqa: E402


def main() -> None:
    config = load_config()
    if not config.can_generate:
        print("ANTHROPIC_API_KEY missing — cannot generate. Set it in .env.")
        sys.exit(1)

    count = max(1, config_posts_per_day(config))
    for _ in range(count):
        carousel = pipeline.generate_and_render(config)
        print(
            f"Drafted {carousel.id} — topic '{carousel.content.topic}', "
            f"{len(carousel.content.slides)} slides. Awaiting your review."
        )


def config_posts_per_day(config) -> int:
    # posts_per_day lives in config.yaml's schedule block; default to 1.
    import yaml

    from app.config import ROOT

    for name in ("config.yaml", "config.example.yaml"):
        path = ROOT / name
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
            return int((data.get("schedule") or {}).get("posts_per_day", 1))
    return 1


if __name__ == "__main__":
    main()
