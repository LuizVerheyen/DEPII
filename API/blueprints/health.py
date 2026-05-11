"""Health-check endpoint.

GET /api/v1/health   → 200 OK + DB-statistieken als de DB bereikbaar is
                       503     als de DB niet bereikbaar is
"""

from flask import Blueprint, jsonify
import logging

from API.db import health_check

bp = Blueprint("health", __name__)
log = logging.getLogger(__name__)


@bp.route("/health", methods=["GET"])
def get_health():
    try:
        result = health_check()
        return jsonify({
            "status": "ok",
            "database": result.get("DatabaseName"),
            "server_time_utc": result.get("ServerTimeUtc"),
            "counts": {
                "counting_points":    result.get("CountingPoints"),
                "weather_stations":   result.get("WeatherStations"),
                "blue_bike_stations": result.get("BlueBikeStations"),
            },
        }), 200
    except Exception as exc:
        log.error("Health-check faalde: %s", exc)
        return jsonify({
            "status": "unavailable",
            "error": str(exc),
        }), 503
