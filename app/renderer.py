"""Render carousel slides to PNGs with Pillow.

Design goals:
  * Look good with zero setup — works with Pillow's bundled DejaVu fonts.
  * Look *great* if you drop nicer fonts into assets/fonts/ (e.g.
    Poppins, Montserrat). We auto-detect Bold/Regular variants there.
  * 1080x1350 (4:5 portrait) — the size Instagram favors for feed reach.

The layout per slide:
  ┌──────────────────────────┐
  │  ●●○○○○○   (progress dots)│
  │                          │
  │   BIG HEADLINE that      │
  │   wraps and auto-fits    │
  │   ──────  (accent bar)   │
  │   supporting body copy   │
  │                          │
  │  @handle          02/07  │
  └──────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import FONTS_DIR
from .models import Carousel, Slide
from .themes import Theme, get_theme

WIDTH, HEIGHT = 1080, 1350
MARGIN = 96

RGB = tuple[int, int, int]


# ── Font discovery ──────────────────────────────────────────────────
# Prefer fonts the user dropped into assets/fonts/, then fall back to a
# few common system locations, then to Pillow's bundled DejaVu.
def _font_candidates(bold: bool) -> list[Path]:
    names_bold = ["Poppins-Bold", "Montserrat-Bold", "Inter-Bold", "DejaVuSans-Bold"]
    names_reg = ["Poppins-Regular", "Montserrat-Regular", "Inter-Regular", "DejaVuSans"]
    stems = names_bold if bold else names_reg

    candidates: list[Path] = []
    for stem in stems:
        for ext in (".ttf", ".otf"):
            candidates.append(FONTS_DIR / f"{stem}{ext}")
    # Common Linux/macOS locations for DejaVu (ships with most distros).
    system = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    candidates.extend(Path(p) for p in system)
    return candidates


def _load_font(size: int, bold: bool) -> ImageFont.FreeTypeFont:
    for path in _font_candidates(bold):
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    # Last resort: Pillow bundles DejaVuSans and resolves it by name.
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


# ── Drawing helpers ─────────────────────────────────────────────────
def _gradient(top: RGB, bottom: RGB) -> Image.Image:
    """Vertical gradient background."""
    base = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(base)
    for y in range(HEIGHT):
        t = y / max(HEIGHT - 1, 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (WIDTH, y)], fill=color)
    return base


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Greedy word wrap to a pixel width."""
    words = text.split()
    if not words:
        return []
    lines, current = [], words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_w:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    max_h: int,
    start_size: int,
    min_size: int,
    bold: bool,
    line_spacing: float = 1.12,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Shrink the font until the wrapped text fits the box."""
    size = start_size
    while size >= min_size:
        font = _load_font(size, bold)
        lines = _wrap(draw, text, font, max_w)
        line_h = (font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) * line_spacing
        if line_h * len(lines) <= max_h:
            return font, lines
        size -= 4
    font = _load_font(min_size, bold)
    return font, _wrap(draw, text, font, max_w)


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    fill: RGB,
    line_spacing: float = 1.12,
) -> int:
    """Draw wrapped lines top-down; return the y below the block."""
    line_h = (font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) * line_spacing
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(line_h)
    return y


def _draw_progress_dots(draw: ImageDraw.ImageDraw, theme: Theme, index: int, total: int) -> None:
    r = 7
    gap = 26
    y = MARGIN
    x = MARGIN + r
    for i in range(total):
        filled = i <= index
        color = theme.accent if filled else theme.muted
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
        x += gap


def _draw_footer(draw: ImageDraw.ImageDraw, theme: Theme, handle: str, index: int, total: int) -> None:
    font = _load_font(34, bold=True)
    y = HEIGHT - MARGIN - 20
    draw.text((MARGIN, y), handle, font=font, fill=theme.accent)
    counter = f"{index + 1:02d} / {total:02d}"
    w = draw.textlength(counter, font=font)
    draw.text((WIDTH - MARGIN - w, y), counter, font=font, fill=theme.muted)


# ── Per-slide rendering ─────────────────────────────────────────────
def _render_slide(slide: Slide, theme: Theme, handle: str, index: int, total: int) -> Image.Image:
    img = _gradient(theme.bg_top, theme.bg_bottom)
    draw = ImageDraw.Draw(img)

    _draw_progress_dots(draw, theme, index, total)

    content_w = WIDTH - 2 * MARGIN
    is_cover = slide.kind == "cover"
    is_cta = slide.kind == "cta"

    # Cover & CTA slides get bigger, more centered headlines.
    if is_cover:
        title_start, title_min = 118, 60
        title_box_h = 560
        top_y = 360
    elif is_cta:
        title_start, title_min = 96, 52
        title_box_h = 460
        top_y = 380
    else:
        title_start, title_min = 84, 46
        title_box_h = 440
        top_y = 300

    # Optional small "kicker" label above the title for non-cover slides.
    cursor_y = top_y
    if not is_cover and not is_cta:
        kicker_font = _load_font(34, bold=True)
        draw.text((MARGIN, cursor_y - 70), f"{index:02d}", font=kicker_font, fill=theme.accent)

    title_font, title_lines = _fit_text(
        draw, slide.title.upper() if is_cover else slide.title,
        content_w, title_box_h, title_start, title_min, bold=True,
    )
    cursor_y = _draw_lines(draw, title_lines, title_font, MARGIN, cursor_y, theme.text)

    # Accent bar under the title.
    cursor_y += 18
    draw.rounded_rectangle(
        [MARGIN, cursor_y, MARGIN + 140, cursor_y + 12], radius=6, fill=theme.accent
    )
    cursor_y += 56

    # Body copy.
    if slide.body.strip():
        body_font, body_lines = _fit_text(
            draw, slide.body, content_w, 360, 48, 30, bold=False, line_spacing=1.25,
        )
        _draw_lines(draw, body_lines, body_font, MARGIN, cursor_y, theme.muted, line_spacing=1.25)

    _draw_footer(draw, theme, handle, index, total)
    return img


# ── Public API ──────────────────────────────────────────────────────
def render_carousel(carousel: Carousel, out_dir: Path, handle: str) -> list[Path]:
    """Render every slide to a PNG; returns the file paths in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    theme = get_theme(carousel.theme)
    slides = carousel.content.slides
    total = len(slides)

    paths: list[Path] = []
    for i, slide in enumerate(slides):
        img = _render_slide(slide, theme, handle, i, total)
        path = out_dir / f"slide_{i + 1:02d}.png"
        img.save(path, "PNG")
        paths.append(path)
    return paths
