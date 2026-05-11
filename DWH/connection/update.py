# update.py
#
# Update van alle DWH-tabellen niet in een cron.
#
# Structuur:
# Update: bouwen → valideren → laden

import logging
import os
import subprocess
import sys

# Voeg logging/ toe aan sys.path zodat logging_config importeerbaar is
_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_pipeline_logging  # noqa: E402

from DWH.connection.connect import get_engine, loadIN
from DWH.connection.validator import (
    LOAD_0_TABLES, LOAD_1_TABLES, LOAD_2_TABLES, UPDATE_VALIDATORS,
    print_report, validate_update, validate_wave,
)

from data_gathering.NMBS.initiator_dimStation import dimStation
from data_gathering.blueBikes.initiator_dimBlueBikeStation import dimBlueBikeStation
from data_gathering.dimDate.initiator import CreateDimDate
from data_gathering.dimLocation.initializer import dimLocation
from data_gathering.dimTime.initiator import dimTime
from data_gathering.email_fietsvergoeding.dimdepartement import dimDepartement, factDepartement
from data_gathering.email_fietsvergoeding.filler import fillDimStaff, fillFactStaffCommute
from data_gathering.mobiliteitsBevragingHOGENT.dimTransportType import fillTransportType
from data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility import dimWM
from data_gathering.mobiliteitsBevragingHOGENT.factMobilityWorker import factWorkerMobility
from data_gathering.telpalen.dimCountingPoint import fillDimCountingPoint
from data_gathering.telpalen.factCountings import fillFactCountings
from data_gathering.weather.initializer import download_weather_for_date
from data_gathering.weather.weatherstationInitializer import download_aws_stations
from data_gathering.studentMobility.fetch_dim_student import fillDimStudent
from data_gathering.studentMobility.fetch_fact_studentmobility import fillFactStudentMobility

logger = logging.getLogger(__name__)


# update tables 
# ────────────────────────────────────────────────────

def run_update(engine) -> bool:
    logger.info("=" * 60)
    logger.info("update tabelen die niet in cronjob staan")
    logger.info("=" * 60)

    candidates = {
        "DimTime": dimTime(),
        "DimDate": CreateDimDate(),
        "DimLocation": dimLocation(),
        "DimTransportType": fillTransportType(),
        "DimDepartement": dimDepartement(),
        "DimBlueBikeStation": dimBlueBikeStation(),
        "DimStation": dimStation(),
        "DimWeatherStation": download_aws_stations(),
        "DimWorkerMobility": dimWM(),
        "DimCountingPoint": fillDimCountingPoint(),
        "DimStaff": fillDimStaff(),
        "DimStudent": fillDimStudent(),
        "FactWorkerMobility": factWorkerMobility(),
        "FactDepartement": factDepartement(),
        "FactStaffCommute": fillFactStaffCommute(),
        "FactStudentMobility": fillFactStudentMobility(),
    }

    report = validate_update(candidates)
    print_report(report)

    if not report.all_passed:
        logger.error("Validatie gefaald bij update — pipeline gestopt. Niets geladen.")
        return False
    
    for table_name in UPDATE_VALIDATORS.keys():
        df = candidates.get(table_name)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.info("  Overgeslagen: %s is leeg — niets te laden.", table_name)
            continue
        kwargs = {"if_exists": "replace"} if table_name == "DimWeatherStation" else {}
        loadIN(engine, df=df, table=table_name, **kwargs)

    return True


# ── Hoofdpipeline ─────────────────────────────────────────────────────────────

def update():
    setup_pipeline_logging()

    # ── Fase 0: unit tests ────────────────────────────────────────────────────
    # Unit tests controleren of de ETL-logica zelf nog correct werkt,
    # volledig los van echte data en echte API's.
    # De pipeline stopt meteen als een test faalt — vóór er ook maar één
    # API-call of DB-verbinding wordt opgezet.
    logger.info("=" * 60)
    logger.info("Fase 0: unit tests draaien...")
    logger.info("=" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unitTests/", "-q", "--tb=short"],
        capture_output=True,
        text=True,
    )
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error("Unit tests gefaald — pipeline gestopt. Geen data geladen.")
        return

    logger.info("Unit tests geslaagd.")

    engine = get_engine()

    # Update
    # ──────────────────────────────────────
    if not run_update(engine):
        return
    logger.info("Update gedaan")

    logger.info("=" * 60)
    logger.info("UPDATE SUCCESVOL AFGEROND")
    logger.info("=" * 60)

if __name__ == "__main__":
    update()
