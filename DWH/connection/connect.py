import logging
import os
import urllib
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd

logger = logging.getLogger(__name__)

load_dotenv()

# Config voor database
SERVER = os.getenv("DB_SERVER", "127.0.0.1,1433")
DATABASE = os.getenv("DB_NAME", "DEPI")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
USER = os.getenv("DB_USER", "sa")
PASSWORD = os.getenv("databasePWD")

def get_engine():
    """Maakt een SQLAlchemy engine."""
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        "Encrypt=yes;"
        # "Trusted_Connection=yes;" # Voor lokaal db
        "TrustServerCertificate=yes;"
    )
    quoted_conn_str = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}", fast_executemany=True)
    return engine

def loadIN(engine, df=None, table=None, if_exists='append'):
    """Laad DataFrame in SQL tabel."""
    if df is None or table is None:
        raise ValueError("df en table zijn verplicht")
    try:
        df.to_sql(
            name=table,
            con=engine,
            if_exists=if_exists,
            index=False,
            chunksize=100,
        )
        logger.info("Succes: Data geladen in %s op %s", table, SERVER)
    except Exception as e:
        logger.exception("Fout bij laden in %s: %s", table, e)
        raise e

def getData(engine, query=None):
    """Haal data op uit database."""
    if query is None:
        raise ValueError("Een SQL-query is verplicht")
    try:
        return pd.read_sql(query, con=engine)
    except Exception as e:
        logger.exception("Fout bij ophalen: %s", e)
        return None

def deleteData(engine, query=None):
    """Verwijder data uit database via een DELETE query."""
    if query is None:
        raise ValueError("Een SQL-query is verplicht")
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text(query))
        logger.info("Succes: Delete uitgevoerd")
    except Exception as e:
        logger.exception("Fout bij verwijderen: %s", e)
        raise e
