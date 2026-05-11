"""DWH-refresh endpoint.

POST /api/v1/dwh/refresh   → forceer een volledige update van de DWH

Roept het update script aan uit DWH/connection/update.py.
Omdat de update lang kan duren, draaien we hem in een aparte thread en
retourneren we onmiddellijk een 202 Accepted met een job-id. De huidige
status kan worden opgevraagd via GET /api/v1/dwh/refresh/<job_id>.

NB: alleen één job tegelijk om dubbele inserts te voorkomen.
"""

from flask import Blueprint, jsonify
from threading import Thread, Lock
from datetime import datetime, timezone
from uuid import uuid4
import logging

bp = Blueprint("dwh", __name__)
log = logging.getLogger(__name__)


_jobs: dict[str, dict] = {}
_jobs_lock = Lock()
_active_job_id: str | None = None


def _run_update(job_id: str) -> None:
    """Importeer en draai de update. Resultaat wordt in _jobs[job_id] gezet."""
    global _active_job_id
    started_at = datetime.now(timezone.utc)
    log.info("DWH-refresh gestart (job_id=%s)", job_id)
    try:
        # Late import zodat de Flask-app niet faalt als deze imports
        # zware dependencies hebben (Selenium, e.d.).
        from DWH.connection.update import update
        update()
        with _jobs_lock:
            _jobs[job_id].update({
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
            })
        log.info("DWH-refresh voltooid (job_id=%s)", job_id)
    except Exception as exc:
        log.exception("DWH-refresh gefaald (job_id=%s): %s", job_id, exc)
        with _jobs_lock:
            _jobs[job_id].update({
                "status": "failed",
                "error": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
            })
    finally:
        with _jobs_lock:
            _active_job_id = None
        # markeer 'started_at' alleen voor debugging
        log.info("DWH-refresh duur: %s", datetime.now(timezone.utc) - started_at)


@bp.route("/dwh/refresh", methods=["POST"])
def trigger_refresh():
    global _active_job_id
    with _jobs_lock:
        if _active_job_id is not None:
            return jsonify({
                "error": "Er loopt al een DWH-refresh.",
                "active_job_id": _active_job_id,
                "status": 409,
            }), 409

        job_id = uuid4().hex[:12]
        _active_job_id = job_id
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat() + "Z",
        }

    Thread(target=_run_update, args=(job_id,), daemon=True, name=f"dwh-refresh-{job_id}").start()

    return jsonify({
        "job_id": job_id,
        "status": "running",
        "status_url": f"/api/v1/dwh/refresh/{job_id}",
    }), 202


@bp.route("/dwh/refresh/<string:job_id>", methods=["GET"])
def refresh_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Onbekende job_id", "status": 404}), 404
    return jsonify(job), 200


@bp.route("/dwh/refresh", methods=["GET"])
def list_refresh_jobs():
    with _jobs_lock:
        jobs = list(_jobs.values())
        active = _active_job_id
    return jsonify({
        "active_job_id": active,
        "count": len(jobs),
        "jobs": jobs,
    }), 200