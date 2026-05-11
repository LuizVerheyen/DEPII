import logging
import os
import sys

_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_pipeline_logging
from DWH.connection.connect import loadIN, get_engine
from DWH.connection.validator import validate_subset, print_report
from data_gathering.telpalen.factCountings import fillFactCountings

setup_pipeline_logging()
logger = logging.getLogger(__name__)
engine = get_engine()

def pipeline():
    try:
        df_fact = fillFactCountings(load_to_db=False)
        if df_fact is not None and not df_fact.empty:
            report = validate_subset({"FactCountings": df_fact}, ["FactCountings"])
            print_report(report)
            if not report.all_passed:
                logger.error("Validatie mislukt — FactCountings niet geladen naar DWH.")
                return
            fillFactCountings(load_to_db=True)
        else:
            logger.info("Geen nieuwe tellingen gevonden.")
    except Exception as e:
        logger.exception("Fout in fillerCountingPoints pipeline")

pipeline()
