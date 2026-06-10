"""Visual themes.

Each theme is a gradient background plus text/accent colors. Kept small
and hand-tuned so every combination looks intentional. Add your own by
dropping a new entry in THEMES.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    name: str
    # Vertical gradient from top → bottom.
    bg_top: RGB
    bg_bottom: RGB
    # Main headline color and the softer body color.
    text: RGB
    muted: RGB
    # Accent used for the bar under the cover title, slide dots, handle.
    accent: RGB

    @property
    def is_dark(self) -> bool:
        r, g, b = self.bg_top
        return (0.299 * r + 0.587 * g + 0.114 * b) < 128


THEMES: dict[str, Theme] = {
    "midnight": Theme(
        name="midnight",
        bg_top=(17, 24, 39),
        bg_bottom=(31, 41, 99),
        text=(248, 250, 252),
        muted=(186, 196, 214),
        accent=(129, 140, 248),
    ),
    "sunrise": Theme(
        name="sunrise",
        bg_top=(255, 154, 108),
        bg_bottom=(255, 99, 132),
        text=(38, 18, 28),
        muted=(74, 38, 48),
        accent=(255, 255, 255),
    ),
    "sunny": Theme(
        name="sunny",
        bg_top=(255, 224, 130),   # warm sunlight gold
        bg_bottom=(255, 159, 67),  # soft orange
        text=(60, 36, 12),         # deep warm brown, high contrast on gold
        muted=(120, 78, 38),
        accent=(229, 57, 53),      # vivid coral-red pop
    ),
    "forest": Theme(
        name="forest",
        bg_top=(20, 58, 47),
        bg_bottom=(8, 28, 22),
        text=(236, 253, 245),
        muted=(167, 200, 188),
        accent=(110, 231, 183),
    ),
    "plum": Theme(
        name="plum",
        bg_top=(46, 16, 70),
        bg_bottom=(91, 33, 121),
        text=(250, 245, 255),
        muted=(206, 188, 226),
        accent=(240, 171, 252),
    ),
    "mono": Theme(
        name="mono",
        bg_top=(244, 244, 245),
        bg_bottom=(228, 228, 231),
        text=(24, 24, 27),
        muted=(82, 82, 91),
        accent=(24, 24, 27),
    ),
    "paper": Theme(
        name="paper",
        # Flat warm cream (editorial look — no gradient).
        bg_top=(244, 241, 233),
        bg_bottom=(244, 241, 233),
        text=(23, 23, 23),       # near-black heavy headlines
        muted=(122, 120, 114),   # warm gray body
        accent=(227, 83, 54),    # editorial orange
    ),
    "ocean": Theme(
        name="ocean",
        bg_top=(8, 47, 73),
        bg_bottom=(12, 74, 110),
        text=(240, 249, 255),
        muted=(170, 207, 230),
        accent=(56, 189, 248),
    ),
    "ember": Theme(
        name="ember",
        bg_top=(40, 12, 12),
        bg_bottom=(96, 24, 16),
        text=(255, 247, 237),
        muted=(224, 184, 166),
        accent=(251, 146, 60),
    ),
}

DEFAULT_THEME = "midnight"


def get_theme(name: str) -> Theme:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    return list(THEMES.keys())
