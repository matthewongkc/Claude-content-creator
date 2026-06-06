# Carousel Studio 🎠

Draft beautiful Instagram carousels with Claude, review and edit them in a
local web dashboard, then auto-post the approved ones to Instagram — on a
daily schedule. **You stay the gatekeeper: nothing publishes without your
approval.**

Topics can be **motivational**, **parenting**, or anything you type in.

```
Claude drafts copy  →  Pillow renders slides  →  you review & edit  →  you approve  →  Instagram posts
        (generator)         (renderer/themes)        (dashboard)         (gate)          (graph API)
```

<!-- A rendered cover + content slide look like clean, bold, gradient cards.
     Run `python run.py sample` to generate a demo set under content/. -->

---

## What you get

- **Claude-drafted copy** — give a topic; Claude writes the hook, the
  content slides, the closing CTA, the caption, and hashtags.
- **You edit before anything ships** — every line is editable in the
  dashboard; re-render with one click.
- **Genuinely nice visuals** — 1080×1350 gradient slides, 7 built-in
  themes, auto-fitting headlines, progress dots, your @handle in the
  footer. Looks good with zero setup; great if you add a font.
- **A real approval gate** — Pending → Approved → Published. The Publish
  button is locked until you approve.
- **Official Instagram auto-posting** — carousels via the Graph API.
- **Daily automation** — a cron/CI script drafts each day; you just review.

---

## Quick start

```bash
# 1. Install
python3 -m pip install -r requirements.txt

# 2. Configure (copy the templates, then edit)
cp .env.example .env                 # add your ANTHROPIC_API_KEY (+ IG keys later)
cp config.example.yaml config.yaml   # set your @handle, theme, topics

# 3. See the visuals immediately — no API key needed
python run.py sample

# 4. Verify your credentials work (read-only — never posts)
python run.py doctor

# 5. Launch the dashboard
python run.py dashboard
#  → open http://localhost:5000  (the "Status" link shows the same checks)
```

In the dashboard, click **+ Generate** (needs `ANTHROPIC_API_KEY`), review
the draft, tweak any text, pick a theme, **Approve**, then **Publish**
(once Instagram is set up — see below).

---

## Configuration

### `config.yaml` (preferences — safe to commit your own copy)

| Key | Meaning |
| --- | --- |
| `brand.handle` | Printed on every slide footer, e.g. `@yourbrand` |
| `brand.theme` | Default theme: `midnight`, `sunrise`, `forest`, `plum`, `mono`, `ocean`, `ember` |
| `content.topics` | Topics the daily job picks from (repeat a topic to weight it) |
| `content.slides_per_carousel` | Slides incl. cover + CTA (2–10) |
| `content.model` | Claude model (default `claude-opus-4-8`) |
| `publishing.auto_post_enabled` | Master switch for posting to Instagram |
| `publishing.require_approval` | Keep `true` — locks Publish until you approve |

### `.env` (secrets — never committed)

`ANTHROPIC_API_KEY` is all you need to generate. The `IG_*`, `IMGBB_*`,
and `CLOUDINARY_*` values are only needed for auto-posting. See
[`.env.example`](.env.example) for the full list.

---

## Setting up Instagram auto-posting

Posting uses the **official Instagram Graph API** (the legitimate route).
One-time setup:

1. **Account type** — your Instagram must be a **Business** or **Creator**
   account, linked to a **Facebook Page**.
2. **Meta app** — create one at <https://developers.facebook.com/> and add
   the *Instagram Graph API* product.
3. **Access token** — generate a **long-lived** access token with the
   `instagram_content_publish`, `instagram_basic`, and
   `pages_read_engagement` permissions.
4. **IDs** — find your Instagram user id (the numeric `IG_USER_ID`).
5. Put `IG_USER_ID` and `IG_ACCESS_TOKEN` in `.env`, and set
   `publishing.auto_post_enabled: true` in `config.yaml`.

> **Why image hosting?** The Graph API fetches each slide from a public
> `image_url` — it won't take raw bytes. So the rendered PNGs are uploaded
> to an image host first. Set `IMAGE_HOST=imgbb` (free; get a key at
> <https://api.imgbb.com/>) or `cloudinary` and fill the matching keys.

**Prefer to post by hand?** Leave `auto_post_enabled: false`. You'll still
get fully rendered slides under `content/<id>/` — just download and upload
them yourself. Everything else (drafting, editing, approving) works.

---

## Scheduling the daily draft

The scheduler only **drafts** — you still approve. Two common options:

**cron** (local machine / server):

```cron
# 8:00 every morning — draft the day's carousel
0 8 * * *  cd /path/to/Claude-content-creator && /usr/bin/python3 scripts/generate_daily.py
```

**GitHub Actions** — a ready-to-use workflow ships at
[`.github/workflows/daily-draft.yml`](.github/workflows/daily-draft.yml).
It runs daily (and on demand), drafts a carousel, and uploads the rendered
slides as a build artifact for review. To enable it: add an
`ANTHROPIC_API_KEY` secret under *Settings → Secrets and variables →
Actions*. It only drafts — it never posts.

You then open the dashboard, review the drafts, and approve the ones you
like.

---

## Command line

```bash
python run.py sample              # render a demo carousel (no API key)
python run.py doctor              # check Claude / image host / Instagram (read-only)
python run.py generate [topic]    # draft + render one carousel
python run.py list                # list all carousels and their status
python run.py publish <id>        # publish an approved carousel
python run.py publish <id> --dry-run   # host images, print URLs, post nothing
python run.py dashboard           # launch the web UI (incl. a Status page)
```

Before your first real post, run `publish <id> --dry-run` — it uploads the
slides to your image host and prints the exact public URLs Instagram would
receive, without posting. A great last sanity check.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite is fully offline (no API keys, no network): model round-trips,
the store, rendering every theme, and the dashboard pages.

---

## How it fits together

```
app/
  config.py      load config.yaml + .env
  models.py      Slide / CarouselContent (Claude's structured output) + Carousel record
  generator.py   Claude API → drafted copy (structured outputs)
  themes.py      7 gradient themes
  renderer.py    Pillow → 1080×1350 slide PNGs
  uploader.py    host images publicly (imgbb / cloudinary)
  instagram.py   Graph API carousel publishing
  pipeline.py    generate → render → approve → publish
  store.py       file-based persistence under content/
  dashboard.py   Flask review/edit/approve/publish UI
scripts/
  generate_daily.py   cron/CI entry — drafts only
run.py           CLI
```

State lives in `content/<id>/` as `carousel.json` + `slide_NN.png`. No
database. Everything is inspectable and portable.

---

## Make the slides even prettier

The renderer uses Pillow's bundled DejaVu Sans by default. Drop a nicer
font (Poppins / Montserrat / Inter) into `assets/fonts/` and it's picked up
automatically — see [`assets/fonts/README.md`](assets/fonts/README.md).

---

## Notes & limits

- A carousel needs **2–10** images (Instagram's limit). `slides_per_carousel`
  is clamped accordingly.
- Long-lived Instagram tokens expire (~60 days) — refresh periodically.
- Generated content is a **draft**. Always read it before approving;
  you're the editor.
