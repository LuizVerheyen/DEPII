"""Flask app factory voor de DEPI Web API."""

import logging
import os
import time
from datetime import datetime

from flask import Flask, request, jsonify

from API.config import Config
from API.errors import register_error_handlers
from API.logging_setup import configure_logging
from API.metrics import metrics_store

# Blueprints
from API.blueprints.health import bp as health_bp
from API.blueprints.dwh import bp as dwh_bp
from API.blueprints.counting import bp as counting_bp
from API.blueprints.weather import bp as weather_bp
from API.blueprints.bluebike import bp as bluebike_bp
from API.blueprints.metrics_bp import bp as metrics_bp
from API.blueprints.extras import bp as extras_bp
from API.blueprints.docs import bp as docs_bp


log = logging.getLogger(__name__)


def create_app() -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Request hooks: meten en loggen ──────────────────────────────────────
    @app.before_request
    def _start_timer():
        request._start_time = time.perf_counter()

    @app.after_request
    def _record_metrics(response):
        start = getattr(request, "_start_time", None)
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000.0
            # Sleutel = METHOD + endpoint-naam (door Flask gegenereerd uit de
            # blueprint + functie). Fallback naar request.path bij 404 e.d.
            endpoint = request.endpoint or request.path
            key = f"{request.method} {endpoint}"
            metrics_store.record(key, duration_ms, response.status_code)

            # Functionele access-log: één regel per request
            access = logging.getLogger("api.access")
            access.info(
                'remote=%s method=%s path="%s" status=%s duration_ms=%.2f endpoint=%s query="%s"',
                request.remote_addr,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                endpoint,
                request.query_string.decode("utf-8", errors="replace"),
            )
        return response

    # ── Root: kleine welkomstpagina ─────────────────────────────────────────
    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "name": "DEPI Data Warehouse REST API",
            "version": "1.0.0",
            "documentation": "/api/v1/docs",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "server_time": datetime.utcnow().isoformat() + "Z",
        })

    # ── Blueprints registreren onder /api/v1 ────────────────────────────────
    api_prefix = "/api/v1"
    app.register_blueprint(health_bp,    url_prefix=api_prefix)
    app.register_blueprint(dwh_bp,       url_prefix=api_prefix)
    app.register_blueprint(counting_bp,  url_prefix=api_prefix)
    app.register_blueprint(weather_bp,   url_prefix=api_prefix)
    app.register_blueprint(bluebike_bp,  url_prefix=api_prefix)
    app.register_blueprint(metrics_bp,   url_prefix=api_prefix)
    app.register_blueprint(extras_bp,    url_prefix=api_prefix)
    app.register_blueprint(docs_bp,      url_prefix=api_prefix)

    register_error_handlers(app)

    log.info("Flask-app gemaakt. Routes geregistreerd onder %s", api_prefix)
    return app
