"""Database-laag voor de Web API.

Alle SQL-aanroepen gaan via stored procedures (zie API/sql/stored_procedures.sql).
We hergebruiken de SQLAlchemy-engine uit DWH/connection/connect.py niet, want
voor stored procedures met OUTPUT/RETURN-waarden en RAISERROR is een directe
pyodbc-cursor handiger.

Functioneel:
    - get_connection()        : context-managed pyodbc.Connection
    - call_proc(proc, params) : roept een SP aan en geeft list-of-dicts terug
"""

from contextlib import contextmanager
from decimal import Decimal
import datetime as _dt
import logging

import pyodbc

from API.config import Config

log = logging.getLogger(__name__)


def _build_connection_string() -> str:
    return (
        f"DRIVER={{{Config.DB_DRIVER}}};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        f"UID={Config.DB_USER};"
        f"PWD={Config.DB_PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


@contextmanager
def get_connection():
    """Context manager rond pyodbc.Connection."""
    conn = pyodbc.connect(_build_connection_string(), autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def _row_to_dict(columns, row):
    """Zet één rij (pyodbc.Row) om naar een JSON-vriendelijk dict."""
    out = {}
    for col, val in zip(columns, row):
        if isinstance(val, Decimal):
            out[col] = float(val)
        elif isinstance(val, (_dt.date, _dt.datetime, _dt.time)):
            out[col] = val.isoformat()
        elif isinstance(val, bytes):
            out[col] = val.hex()
        else:
            out[col] = val
    return out


def call_proc(proc_name: str, params: tuple = ()) -> list[dict]:
    """Roep een stored procedure aan en geef alle rijen terug als list-of-dicts.

    Args:
        proc_name : naam van de stored procedure (bv. 'dbo.sp_HealthCheck')
        params    : tuple van invoerparameters in volgorde

    Raises:
        pyodbc.Error : DB-fouten (incl. RAISERROR uit de SP)
    """
    placeholders = ", ".join(["?"] * len(params))
    sql = f"EXEC {proc_name} {placeholders}".strip()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)

        # Skip eventuele lege resultsets (door SET NOCOUNT-trucs niet nodig,
        # maar safe).
        while cursor.description is None:
            if not cursor.nextset():
                return []

        columns = [col[0] for col in cursor.description]
        rows = [_row_to_dict(columns, r) for r in cursor.fetchall()]
        cursor.close()
        return rows


def health_check() -> dict:
    """Roep sp_HealthCheck aan; returnt het dict van de eerste rij."""
    rows = call_proc("dbo.sp_HealthCheck")
    return rows[0] if rows else {"Status": "unknown"}
