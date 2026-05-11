"""Configuratie voor de Flask Web API.

Alle omgevingsvariabelen worden geladen via python-dotenv vanuit de
projectwortel (.env). De DB-instellingen volgen dezelfde conventies als
DWH/connection/connect.py.
"""

import os
from dotenv import load_dotenv

# Laad .env vanuit de projectwortel (één niveau boven deze map)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


class Config:
    # ── Flask ────────────────────────────────────────────────────────────────
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "5000"))
    DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"
    JSON_SORT_KEYS = False

    # ── Database (zelfde als DWH/connection/connect.py) ─────────────────────
    DB_SERVER = os.getenv("DB_SERVER", "127.0.0.1,1433")
    DB_NAME = os.getenv("DB_NAME", "DEPI")
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_USER = os.getenv("DB_USER", "sa")
    DB_PASSWORD = os.getenv("databasePWD", "")

    # ── Logging ─────────────────────────────────────────────────────────────
    LOG_DIR = os.getenv("API_LOG_DIR", os.path.join(_PROJECT_ROOT, "logging", "webapi"))
    LOG_LEVEL = os.getenv("API_LOG_LEVEL", "INFO")

    # ── Project root ────────────────────────────────────────────────────────
    PROJECT_ROOT = _PROJECT_ROOT

    # ── DWH refresh ─────────────────────────────────────────────────────────
    # Maximaal toegestane refresh-tijd in seconden
    DWH_REFRESH_TIMEOUT = int(os.getenv("DWH_REFRESH_TIMEOUT", "1800"))
