"""Draft carousel copy with Claude.

We use Claude's structured outputs (`messages.parse`) so the model returns
a validated `CarouselContent` — cover slide, content slides, a closing CTA,
plus an Instagram caption and hashtags. You then edit it in the dashboard
before anything gets rendered or posted: Claude drafts, you decide.
"""

from __future__ import annotations

import anthropic

from .config import Config
from .models import CarouselContent

SYSTEM_PROMPT = """\
You are a senior social-media content designer who writes high-performing \
Instagram carousels. You write for a thoughtful, busy audience and avoid \
clichés, hype, and empty motivation. Your copy is concrete, warm, and \
genuinely useful.

Carousel craft rules:
- Slide 1 (cover) is a scroll-stopping hook: a bold promise, a sharp \
  question, or a counter-intuitive truth. Short — a few words to a short \
  sentence. No "swipe to learn more".
- Middle slides each make ONE point. Title = the idea in a few punchy \
  words; body = one or two plain-spoken sentences that pay it off.
- Final slide (cta) is a gentle, specific call to action — save, share, \
  try one thing today, or follow for more. Not salesy.
- Keep every title short enough to render large on a phone. Bodies are \
  tight; no rambling.
- The caption expands on the theme in 2-4 sentences and invites a comment. \
  Do NOT put hashtags in the caption; return them separately.
- Hashtags: a focused mix (8-15) of niche + medium-reach tags relevant to \
  the topic. No spaces, no # sign in the values.
"""

USER_TEMPLATE = """\
Create one Instagram carousel.

Topic: {topic}
Number of slides (including cover and closing CTA): {n_slides}

Return exactly {n_slides} slides:
- The first slide has kind "cover".
- The last slide has kind "cta".
- All slides in between have kind "point".
"""


def _topic_brief(topic: str) -> str:
    """Expand the shorthand topics into a richer brief for the model."""
    presets = {
        "motivational": (
            "motivation and personal growth — discipline, momentum, mindset, "
            "showing up on hard days. Grounded and practical, not toxic hustle."
        ),
        "parenting": (
            "modern parenting — connection over control, emotional regulation, "
            "small daily habits, raising resilient kids. Compassionate, realistic."
        ),
    }
    return presets.get(topic.strip().lower(), topic)


def generate(config: Config, topic: str | None = None) -> CarouselContent:
    """Draft a carousel for `topic` (or a config-chosen topic)."""
    if not config.secrets.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env to generate copy."
        )

    chosen = topic or config.content.pick_topic()
    brief = _topic_brief(chosen)
    n_slides = max(3, config.content.slides_per_carousel)

    client = anthropic.Anthropic(api_key=config.secrets.anthropic_api_key)

    response = client.messages.parse(
        model=config.content.model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(topic=brief, n_slides=n_slides),
            }
        ],
        output_format=CarouselContent,
    )

    content = response.parsed_output
    if content is None:
        raise RuntimeError(
            f"Claude did not return valid structured copy (stop_reason="
            f"{response.stop_reason})."
        )

    # Keep the human-facing topic label rather than the expanded brief.
    content.topic = chosen
    return content
