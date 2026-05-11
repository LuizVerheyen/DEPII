# initiator.py
#
# Hoofdpipeline voor de initiële en dagelijkse load van alle DWH-tabellen.
#
# Structuur:
#   Fase 0  — Unit tests: stoppen als een test faalt
#   Load 0  — Onafhankelijke dimensies: bouwen → valideren → laden
#   Load 1  — Afhankelijke dimensies:   bouwen → valideren → laden
#   Load 2  — Feitentabellen:           bouwen → valideren → laden

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
    LOAD_0_TABLES, LOAD_1_TABLES, LOAD_2_TABLES,
    print_report, validate_wave,
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


# ── Hulpfunctie ───────────────────────────────────────────────────────────────

def _load_wave(engine, candidates: dict, wave: str) -> bool:
    """
    Valideert en laadt één golf van tabellen.

    Werkwijze:
      1. Valideer alle tabellen in de golf.
      2. Als validatie faalt → niets laden, pipeline stoppen (return False).
      3. Als validatie slaagt → elke niet-lege tabel naar de DB schrijven.

    Bijzonderheden:
      - DimWeatherStation gebruikt if_exists='replace' (volledige snapshot).
      - FactCountings wordt hier NIET geladen; die tabel schrijft zichzelf
        rechtstreeks via fillFactCountings(load_to_db=True) — zie run_load_2().
      - Lege DataFrames worden overgeslagen zonder fout.
    """
    report = validate_wave(candidates, wave)
    print_report(report)

    if not report.all_passed:
        logger.error("Validatie gefaald in %s — pipeline gestopt. Niets geladen.", wave)
        return False

    if wave == "load_0":
        tables = LOAD_0_TABLES
    elif wave == "load_1":
        tables = LOAD_1_TABLES
    else:
        tables = LOAD_2_TABLES

    for table_name in tables:
        # FactCountings wordt apart afgehandeld in run_load_2()
        if table_name == "FactCountings":
            continue

        df = candidates.get(table_name)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.info("  Overgeslagen: %s is leeg — niets te laden.", table_name)
            continue

        kwargs = {"if_exists": "replace"} if table_name == "DimWeatherStation" else {}
        loadIN(engine, df=df, table=table_name, **kwargs)

    return True


# ── Load-functies per golf ────────────────────────────────────────────────────

def run_load_0(engine) -> bool:
    """
    Onafhankelijke dimensies — geen getData()-calls intern.

    DimTime          : gegenereerd uit Python-logica (1440 minuten)
    DimDate          : gegenereerd via externe API's (feestdagen, schoolvakanties)
    DimLocation      : geladen uit vaste Excel (postcodes)
    DimTransportType : geladen uit vaste CSV (CO2-uitstoot per transportmiddel)
    DimDepartement   : geladen uit Excel (departementen via e-mail)

    Deze tabellen moeten IN de DB staan vóór load_1 kan starten, omdat load_1-functies
    getData()-calls doen op DimLocation en DimDepartement.
    """
    logger.info("=" * 60)
    logger.info("Load 0: onafhankelijke dimensies bouwen, valideren en laden...")
    logger.info("  (DimTime, DimDate, DimLocation, DimTransportType, DimDepartement)")
    logger.info("=" * 60)

    candidates = {
        "DimTime":          dimTime(),
        "DimDate":          CreateDimDate(),
        "DimLocation":      dimLocation(),
        "DimTransportType": fillTransportType(),
        "DimDepartement":   dimDepartement(),
    }

    return _load_wave(engine, candidates, "load_0")


def run_load_1(engine) -> bool:
    """
    Afhankelijke dimensies — doen intern getData()-calls op eerder geladen tabellen.

    DimBlueBikeStation : getData() op DimLocation (LocationKey via postcode)
    DimStation         : getData() op DimBlueBikeStation + DimLocation
                         → DimBlueBikeStation-data wordt direct meegegeven als argument
                           om een extra DB-roundtrip te vermijden
    DimWeatherStation  : getLocationKey() → getData() op DimLocation
    DimWorkerMobility  : getLocationKey() → getData() op DimLocation
    DimCountingPoint   : getData() op DimLocation
    DimStaff           : getData() op DimDepartement (DepartementKey)
    DimStudent         : getData() op DimDepartement (DepartementKey)
    """
    logger.info("=" * 60)
    logger.info("Load 1: afhankelijke dimensies bouwen, valideren en laden...")
    logger.info("  (DimBlueBikeStation, DimStation, DimWeatherStation,")
    logger.info("   DimWorkerMobility, DimCountingPoint, DimStaff, DimStudent)")
    logger.info("=" * 60)

    # DimBlueBikeStation eerst bouwen zodat dimStation() de data direct
    # als argument krijgt — efficiënter dan een extra getData()-call.
    df_bluebike_station = dimBlueBikeStation()

    candidates = {
        "DimBlueBikeStation": df_bluebike_station,
        "DimStation": dimStation(df_bluebike_station.copy() if df_bluebike_station is not None else None),
        "DimWeatherStation": download_aws_stations(),
        "DimWorkerMobility": dimWM(),
        "DimCountingPoint": fillDimCountingPoint(),
        "DimStaff": fillDimStaff(),
        "DimStudent": fillDimStudent(),
    }

    return _load_wave(engine, candidates, "load_1")


def run_load_2(engine) -> bool:
    """
    Feitentabellen — alle dimensies zijn nu in de DB aanwezig.

    FactWorkerMobility  : getData() op DimWorkerMobility + DimTransportType
    FactDepartement     : getData() op DimDepartement
    FactStaffCommute    : getData() op DimStaff + DimDate
    FactCountings       : getData() op DimCountingPoint
                          → Speciale behandeling: fillFactCountings() schrijft
                            zichzelf rechtstreeks naar de DB (load_to_db=True).
                            Voor validatie wordt eerst load_to_db=False gebruikt.
    FactStudentMobility : getData() op DimStudent + DimTransportType + DimDate
    FactMeteo           : geen getData()-call; DateKey via DimDate FK bij load
    """
    logger.info("=" * 60)
    logger.info("Load 2: feitentabellen bouwen, valideren en laden...")
    logger.info("  (FactWorkerMobility, FactDepartement, FactStaffCommute,")
    logger.info("   FactCountings, FactStudentMobility, FactMeteo)")
    logger.info("=" * 60)

    candidates = {
        "FactWorkerMobility": factWorkerMobility(),
        "FactDepartement": factDepartement(),
        "FactStaffCommute": fillFactStaffCommute(),
        "FactCountings": fillFactCountings(load_to_db=False),   # alleen voor validatie
        "FactStudentMobility": fillFactStudentMobility(),
        "FactMeteo": download_weather_for_date(),
    }

    report_passed = _load_wave(engine, candidates, "load_2")
    if not report_passed:
        return False

    # FactCountings apart laden: de ETL-functie schrijft zelf naar de DB
    # (incrementeel, per telpaal) om RAM-gebruik te beperken.
    logger.info("  FactCountings laden via fillFactCountings(load_to_db=True)...")
    fillFactCountings(load_to_db=True)

    return True


# ── Hoofdpipeline ─────────────────────────────────────────────────────────────

def pipeline():
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

    # ── Load 0: onafhankelijke dimensies ──────────────────────────────────────
    if not run_load_0(engine):
        return
    logger.info("Load 0 geladen.")

    # ── Load 1: afhankelijke dimensies ────────────────────────────────────────
    if not run_load_1(engine):
        return
    logger.info("Load 1 geladen.")

    # ── Load 2: feitentabellen ────────────────────────────────────────────────
    if not run_load_2(engine):
        return

    logger.info("=" * 60)
    logger.info("PIPELINE SUCCESVOL AFGEROND")
    logger.info("=" * 60)


if __name__ == "__main__":
    pipeline()
