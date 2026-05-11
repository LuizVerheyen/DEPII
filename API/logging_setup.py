"""Logging-configuratie voor de Web API.

Alle logs (technisch + access) gaan naar één bestand: logging/webapi/webapi.log.

Daarnaast bestaat er een in-memory metrics-store (zie API/metrics.py) die
het aantal calls en de gemiddelde + maximale responstijd per endpoint
bijhoudt. Beide samen voldoen aan studiewijzer-eis 3.05.
"""

import logging
import logging.handlers
import os

from API.config import Config


def configure_logging() -> None:
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # Voorkom dubbele handlers bij hot-reload
    root.handlers = [h for h in root.handlers if not getattr(h, "_api_managed", False)]

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(Config.LOG_DIR, "webapi.log"),
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._api_managed = True
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console._api_managed = True
    root.addHandler(console)
