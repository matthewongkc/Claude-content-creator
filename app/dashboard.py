"""The gatekeeper dashboard — a small Flask app.

Run it, open http://localhost:5000, and you'll see every carousel with
live previews. From there you can:
  * Generate a new draft (pick a topic or type your own)
  * Edit every slide's copy, the caption, hashtags, and theme
  * Re-render to see your edits
  * Approve / Reject
  * Publish approved carousels to Instagram

Nothing posts without your click.
"""

from __future__ import annotations

from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from . import diagnostics, pipeline, store
from .config import CONTENT_DIR, load_config
from .models import CarouselContent, Slide, Status
from .themes import theme_names


def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = config.secrets.dashboard_secret

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "brand": config.brand,
            "themes": theme_names(),
            "can_generate": config.can_generate,
            "can_publish": config.can_publish,
            "require_approval": config.publishing.require_approval,
            "Status": Status,
        }

    # ── Listing ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        status_filter = request.args.get("status")
        carousels = store.list_all()
        if status_filter:
            carousels = [c for c in carousels if c.status.value == status_filter]
        counts = {s: 0 for s in Status}
        for c in store.list_all():
            counts[c.status] += 1
        return render_template(
            "index.html", carousels=carousels, counts=counts, active=status_filter
        )

    # ── Status / health ────────────────────────────────────────────
    @app.route("/status")
    def status():
        results = diagnostics.run_all(config)
        return render_template("status.html", results=results, config=config)

    # ── Detail / edit ──────────────────────────────────────────────
    @app.route("/carousel/<carousel_id>")
    def detail(carousel_id: str):
        carousel = store.load(carousel_id)
        if not carousel:
            abort(404)
        return render_template("detail.html", c=carousel)

    @app.route("/carousel/<carousel_id>/edit", methods=["POST"])
    def edit(carousel_id: str):
        carousel = store.load(carousel_id)
        if not carousel:
            abort(404)

        form = request.form
        n = int(form.get("slide_count", 0))
        slides: list[Slide] = []
        for i in range(n):
            title = form.get(f"title_{i}", "").strip()
            body = form.get(f"body_{i}", "").strip()
            kind = form.get(f"kind_{i}", "point").strip() or "point"
            if title or body:
                slides.append(Slide(kind=kind, title=title, body=body))

        hashtags = [
            t.strip().lstrip("#")
            for t in form.get("hashtags", "").replace(",", " ").split()
            if t.strip()
        ]

        carousel.content = CarouselContent(
            topic=form.get("topic", carousel.content.topic).strip(),
            slides=slides,
            caption=form.get("caption", "").strip(),
            hashtags=hashtags,
        )
        carousel.theme = form.get("theme", carousel.theme)
        # Editing a published/rejected item sends it back to review.
        if carousel.status in (Status.PUBLISHED, Status.REJECTED, Status.FAILED):
            carousel.status = Status.PENDING
        store.save(carousel)
        pipeline.rerender(config, carousel)
        flash("Saved and re-rendered.", "ok")
        return redirect(url_for("detail", carousel_id=carousel_id))

    # ── Status transitions ─────────────────────────────────────────
    @app.route("/carousel/<carousel_id>/approve", methods=["POST"])
    def approve(carousel_id: str):
        carousel = store.load(carousel_id)
        if not carousel:
            abort(404)
        carousel.status = Status.APPROVED
        store.save(carousel)
        flash("Approved — ready to publish.", "ok")
        return redirect(url_for("detail", carousel_id=carousel_id))

    @app.route("/carousel/<carousel_id>/reject", methods=["POST"])
    def reject(carousel_id: str):
        carousel = store.load(carousel_id)
        if not carousel:
            abort(404)
        carousel.status = Status.REJECTED
        store.save(carousel)
        flash("Rejected.", "ok")
        return redirect(url_for("detail", carousel_id=carousel_id))

    @app.route("/carousel/<carousel_id>/publish", methods=["POST"])
    def publish(carousel_id: str):
        carousel = store.load(carousel_id)
        if not carousel:
            abort(404)
        try:
            pipeline.publish(config, carousel)
            flash("Published to Instagram! 🎉", "ok")
        except Exception as exc:  # noqa: BLE001
            flash(f"Publish failed: {exc}", "error")
        return redirect(url_for("detail", carousel_id=carousel_id))

    # ── Generation ─────────────────────────────────────────────────
    @app.route("/generate", methods=["POST"])
    def generate():
        if not config.can_generate:
            flash("Set ANTHROPIC_API_KEY in .env to generate drafts.", "error")
            return redirect(url_for("index"))
        topic = request.form.get("topic", "").strip() or None
        try:
            carousel = pipeline.generate_and_render(config, topic)
            flash("New draft generated.", "ok")
            return redirect(url_for("detail", carousel_id=carousel.id))
        except Exception as exc:  # noqa: BLE001
            flash(f"Generation failed: {exc}", "error")
            return redirect(url_for("index"))

    # ── Serve rendered slide images ────────────────────────────────
    @app.route("/image/<carousel_id>/<filename>")
    def image(carousel_id: str, filename: str):
        safe = Path(filename).name  # prevent path traversal
        path = CONTENT_DIR / carousel_id / safe
        if not path.exists():
            abort(404)
        return send_file(path, mimetype="image/png")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
