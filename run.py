"""Receipt Spending Analyzer — Flask entry point.

Scan receipts, auto-categorise line items with an LLM, and turn a shoebox of
crumpled paper into clean spending reports, budgets and AI-powered advice.
"""

import os

from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone

from app.routes.workspace import workspace_bp
from app.routes.categories import categories_dp
from app.routes.reciepts import reciepts_bp
from app.routes.transactions import transaction_bp
from app.routes.reports import report_bp
from app.routes.insights import insights_bp
from app.utils.save_reciept_image import save_receipt_image
from app.utils.reciept_parser import reciept_parser


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

    # Register the API blueprints (each owns one slice of the domain).
    app.register_blueprint(workspace_bp)
    app.register_blueprint(categories_dp)
    app.register_blueprint(reciepts_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(insights_bp)

    @app.route("/")
    def home():
        """Friendly landing page + live API map."""
        return render_template("index.html")

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
            if not file:
                return "No file uploaded", 400
            receipt_id, path = save_receipt_image(file)
            img_url = os.path.basename(path)
            extracted = reciept_parser(img_url, instance_id)
            return jsonify(
                {"receipt_id": receipt_id, "path": path, "json": extracted}
            )
        return render_template("upload.html")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
