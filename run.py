#!/usr/bin/env python3
"""Command-line entry point.

Usage:
  python run.py dashboard                # launch the review/approve web UI
  python run.py doctor                   # check Claude / image host / Instagram
  python run.py generate [TOPIC]         # draft + render one carousel
  python run.py list                     # show all carousels and status
  python run.py publish <CAROUSEL_ID>    # publish an approved carousel
  python run.py publish <ID> --dry-run   # rehearse publish (host images, no post)
  python run.py sample                   # render a demo carousel (no API key)

The dashboard is the main way to work. The CLI is handy for cron jobs and
quick checks.
"""

from __future__ import annotations

import sys

from app import pipeline, store
from app.config import load_config
from app.models import CarouselContent, Slide, Status


def _cmd_dashboard() -> None:
    from app.dashboard import app

    print("Carousel Studio → http://localhost:5000  (Ctrl-C to stop)")
    app.run(debug=False, port=5000)


def _cmd_generate(args: list[str]) -> None:
    config = load_config()
    topic = " ".join(args) or None
    carousel = pipeline.generate_and_render(config, topic)
    print(f"Generated {carousel.id} ({carousel.content.topic}) — status: {carousel.status.value}")
    print(f"Slides in: content/{carousel.id}/")
    print("Review it in the dashboard before publishing.")


def _cmd_list() -> None:
    carousels = store.list_all()
    if not carousels:
        print("No carousels yet. Run:  python run.py generate")
        return
    for c in carousels:
        title = c.content.slides[0].title if c.content.slides else "(empty)"
        print(f"{c.id}  {c.status.value:<9}  {c.content.topic:<14}  {title[:48]}")


def _cmd_doctor() -> None:
    from app import diagnostics

    config = load_config()
    print("Checking integrations…\n")
    results = diagnostics.run_all(config)
    for r in results:
        print(f"  {r.icon}  {r.name:<26}  {r.detail}")
    ready = all(r.ok for r in results)
    print()
    if ready:
        print("All systems go. You can generate, approve, and publish.")
    else:
        print("Some checks failed — fix the above, then re-run `python run.py doctor`.")
        print("(Generation only needs Claude; posting needs the image host + Instagram.)")


def _cmd_publish(args: list[str]) -> None:
    positional = [a for a in args if not a.startswith("-")]
    dry_run = "--dry-run" in args
    if not positional:
        print("Usage: python run.py publish <CAROUSEL_ID> [--dry-run]")
        sys.exit(1)
    config = load_config()
    carousel = store.load(positional[0])
    if not carousel:
        print(f"No carousel with id {positional[0]}")
        sys.exit(1)
    if dry_run:
        urls = pipeline.dry_run_publish(config, carousel)
        print("Dry run OK — images hosted, nothing posted. Public URLs:")
        for u in urls:
            print(f"  {u}")
        return
    carousel = pipeline.publish(config, carousel)
    print(f"Published! {carousel.instagram_permalink}")


def _cmd_sample() -> None:
    """Render a demo carousel locally — no API key needed. Great for a quick
    look at the visual output before wiring up Claude."""
    config = load_config()
    content = CarouselContent(
        topic="motivational",
        slides=[
            Slide(kind="cover", title="Start before you feel ready", body=""),
            Slide(
                kind="point",
                title="Motivation follows action",
                body="You don't wait to feel like it. You move, and the feeling catches up.",
            ),
            Slide(
                kind="point",
                title="Shrink the first step",
                body="Make it so small it feels silly to skip. Two minutes counts.",
            ),
            Slide(
                kind="point",
                title="Show up on the bad days",
                body="Consistency isn't intensity. It's returning when it's boring.",
            ),
            Slide(
                kind="cta",
                title="Pick one tiny thing. Do it today.",
                body="Save this as a reminder, and follow for more.",
            ),
        ],
        caption="The gap between you and the thing you want is usually one small, "
        "unglamorous action — taken today instead of someday. Which one will you take?",
        hashtags=["motivation", "discipline", "mindset", "growth", "habits", "consistency"],
    )
    carousel = pipeline.create_from_content(config, content, theme=config.brand.theme)
    print(f"Rendered sample {carousel.id} → content/{carousel.id}/")
    print("Open the dashboard (python run.py dashboard) to see it.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, rest = sys.argv[1], sys.argv[2:]
    dispatch = {
        "dashboard": lambda: _cmd_dashboard(),
        "doctor": lambda: _cmd_doctor(),
        "generate": lambda: _cmd_generate(rest),
        "list": lambda: _cmd_list(),
        "publish": lambda: _cmd_publish(rest),
        "sample": lambda: _cmd_sample(),
    }
    handler = dispatch.get(cmd)
    if not handler:
        print(__doc__)
        sys.exit(1)
    handler()


if __name__ == "__main__":
    main()
