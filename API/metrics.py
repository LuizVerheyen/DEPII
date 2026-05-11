"""In-memory metrics-store per endpoint.

Voldoet aan studiewijzer-eis 3.05:
    - Het aantal keer dat elk type request/elke operatie uitgevoerd werd.
    - De gemiddelde en maximale responstijd per type request/operatie.

We gebruiken een simpele thread-safe dict; voldoende voor een single-process
Flask-app op de DEP-VM.
"""

from collections import defaultdict
from threading import Lock


class MetricsStore:
    """Thread-safe per-endpoint counters + responstijd-statistieken."""

    def __init__(self):
        self._lock = Lock()
        self._data = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "total_ms": 0.0,
            "max_ms": 0.0,
            "min_ms": None,
            "last_status": None,
        })

    def record(self, key: str, duration_ms: float, status_code: int) -> None:
        with self._lock:
            entry = self._data[key]
            entry["count"] += 1
            entry["total_ms"] += duration_ms
            entry["max_ms"] = max(entry["max_ms"], duration_ms)
            entry["min_ms"] = (
                duration_ms if entry["min_ms"] is None
                else min(entry["min_ms"], duration_ms)
            )
            entry["last_status"] = status_code
            if status_code >= 400:
                entry["errors"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            out = {}
            for key, entry in self._data.items():
                count = entry["count"]
                avg_ms = (entry["total_ms"] / count) if count else 0.0
                out[key] = {
                    "count": count,
                    "errors": entry["errors"],
                    "avg_ms": round(avg_ms, 2),
                    "max_ms": round(entry["max_ms"], 2),
                    "min_ms": round(entry["min_ms"], 2) if entry["min_ms"] is not None else None,
                    "last_status": entry["last_status"],
                }
            return out

    def reset(self) -> None:
        with self._lock:
            self._data.clear()


# Singleton voor de app
metrics_store = MetricsStore()
