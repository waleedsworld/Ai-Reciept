"""HTTP surface for recurring-charge (subscription) detection."""

from flask import Blueprint, jsonify, render_template, request

from app.services.recurring import detect_recurring

recurring_bp = Blueprint("recurring_bp", __name__)


@recurring_bp.route("/v1/instances/<id>/recurring", methods=["GET"])
def get_recurring_route(id):
    """Surface the recurring charges detected for a workspace.

    Query params (both optional):
      * ``min_occurrences`` — separate purchase days needed to qualify (default 3).
      * ``max_variability`` — how metronome-like gaps must be, 0..1 (default 0.4).
    """
    try:
        min_occurrences = int(request.args.get("min_occurrences", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "min_occurrences must be an integer"}), 400
    if min_occurrences < 2:
        return jsonify({"error": "min_occurrences must be at least 2"}), 400

    try:
        max_variability = float(request.args.get("max_variability", 0.4))
    except (TypeError, ValueError):
        return jsonify({"error": "max_variability must be a number"}), 400
    if not 0 < max_variability <= 1:
        return jsonify({"error": "max_variability must be between 0 and 1"}), 400

    resp, code = detect_recurring(id, min_occurrences, max_variability)
    return jsonify(resp), code


@recurring_bp.route("/recurring", methods=["GET"])
def recurring_view():
    """Subscription Radar — a small dashboard over the recurring-charge API."""
    return render_template("recurring.html")
