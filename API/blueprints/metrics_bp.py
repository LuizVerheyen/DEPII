"""Metrics-endpoint.

GET /api/v1/metrics       → snapshot van per-endpoint counters en
                            gemiddelde/maximale responstijden.
DELETE /api/v1/metrics    → reset (voor demo/eindevaluatie).
"""

from flask import Blueprint, jsonify
from datetime import datetime

from API.metrics import metrics_store

bp = Blueprint("metrics", __name__)


@bp.route("/metrics", methods=["GET"])
def get_metrics():
    snap = metrics_store.snapshot()
    totals = sum(v["count"] for v in snap.values())
    return jsonify({
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_requests": totals,
        "endpoints": snap,
    }), 200


@bp.route("/metrics", methods=["DELETE"])
def reset_metrics():
    metrics_store.reset()
    return jsonify({"status": "reset"}), 200
