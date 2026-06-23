"""Receipt Spending Analyzer — Flask entry point.

Scan receipts, auto-categorise line items with an LLM, and turn a shoebox of
crumpled paper into clean spending reports, budgets and AI-powered advice.
"""

import os

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)
from datetime import datetime, timezone

from app.routes.workspace import workspace_bp
from app.routes.categories import categories_dp
from app.routes.reciepts import reciepts_bp
from app.routes.transactions import transaction_bp
from app.routes.reports import report_bp
from app.routes.insights import insights_bp
from app.routes.recurring import recurring_bp
from app.errors import register_error_handlers
from app.utils.save_reciept_image import save_receipt_image, UnsupportedFileType
from app.utils.reciept_parser import reciept_parser


# Cap request bodies so an oversized (or malicious) upload can't exhaust memory
# or disk. Werkzeug raises 413 automatically once this is exceeded.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "16")) * 1024 * 1024


# --- Storage bootstrap -------------------------------------------------------
# The app persists everything to lightweight CSV/JSON files under ./storage.
# Make sure every folder an endpoint might write to exists before we serve a
# single request, so a fresh clone "just works".
STORAGE_DIRS = [
    "storage",
    "storage/instances",
    "storage/receipts/uploads",
    "storage/charts",
]
for _d in STORAGE_DIRS:
    os.makedirs(_d, exist_ok=True)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    # Uniform JSON error responses (404/405/413/500/…) across the API.
    register_error_handlers(app)

    # Register the API blueprints (each owns one slice of the domain).
    app.register_blueprint(workspace_bp)
    app.register_blueprint(categories_dp)
    app.register_blueprint(reciepts_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(recurring_bp)

    def _base_url() -> str:
        """Absolute site origin used for canonical / Open Graph / sitemap URLs.

        Prefers the SITE_URL env var (set it to your public domain in prod, e.g.
        https://receipts.example.com); otherwise falls back to the request host
        so links stay correct on localhost and any deployment.
        """
        env = os.environ.get("SITE_URL")
        base = env or request.host_url
        return base.rstrip("/")

    @app.context_processor
    def inject_seo():
        """Expose SEO helpers (absolute base URL + canonical) to every template."""
        base = _base_url()
        return {
            "base_url": base,
            "canonical_url": base + request.path.rstrip("/") if request.path != "/" else base + "/",
        }

    @app.route("/")
    def home():
        """Friendly landing page + live API map.

        Supports a lightweight A/B test of the hero via ?variant=b. The choice
        is remembered in a cookie so a visitor stays in the same bucket across
        reloads; ?variant=a (or clearing it) returns to the default landing.
        """
        variant = request.args.get("variant")
        if variant not in ("a", "b"):
            variant = request.cookies.get("landing_variant", "a")
        template = "index_b.html" if variant == "b" else "index.html"
        resp = app.make_response(render_template(template))
        resp.set_cookie("landing_variant", variant, max_age=60 * 60 * 24 * 30)
        return resp

    @app.route("/robots.txt")
    def robots_txt():
        body = (
            "User-agent: *\n"
            "Allow: /$\n"
            "Allow: /upload\n"
            "Disallow: /v1/\n"
            "Disallow: /static/\n\n"
            f"Sitemap: {_base_url()}/sitemap.xml\n"
        )
        return Response(body, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        base = _base_url()
        today = datetime.now(timezone.utc).date().isoformat()
        pages = [("/", "1.0"), ("/upload", "0.7")]
        urls = "".join(
            f"  <url><loc>{base}{path}</loc><lastmod>{today}</lastmod>"
            f"<priority>{prio}</priority></url>\n"
            for path, prio in pages
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n"
        )
        return Response(xml, mimetype="application/xml")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            app.static_folder, "favicon.ico", mimetype="image/x-icon"
        )

    @app.route("/v1/health", methods=["GET"])
    def check_health():
        return {
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),
        }

    # Quick manual receipt upload for local testing / demos.
    @app.route("/upload", methods=["GET", "POST"])
    def upload_receipt():
        if request.method == "POST":
            file = request.files.get("reciept")
            instance_id = request.form.get("instance_id", "demo")
            if not file or not file.filename:
                return jsonify({"error": "No file uploaded", "status": 400}), 400
            try:
                receipt_id, path = save_receipt_image(file)
            except UnsupportedFileType as exc:
                return jsonify({"error": str(exc), "status": 415}), 415
            img_url = os.path.basename(path)
            try:
                extracted = reciept_parser(img_url, instance_id)
            except Exception as exc:  # noqa: BLE001
                # Parsing depends on an external LLM + a valid API key. If that
                # is missing or the call fails, still return the saved receipt
                # with a clear message instead of a 500 stack trace.
                app.logger.warning("Receipt parse failed: %s", exc)
                extracted = {
                    "error": "Receipt saved but parsing failed. "
                    "Check that OPENAI_API_KEY is set.",
                }
            return jsonify(
                {"receipt_id": receipt_id, "path": path, "json": extracted}
            )
        return render_template("upload.html")

    return app


app = create_app()


def main() -> None:
    """Console entry point (``receipt-analyzer``) — run the dev server.

    Honours ``PORT`` (default 5000) and ``FLASK_DEBUG`` (default on).
    """
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
