import logging
import os
import sys

_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_pipeline_logging
from DWH.connection.connect import loadIN, get_engine
from DWH.connection.validator import validate_subset, print_report
from data_gathering.blueBikes.fetch_fact_bluebike import factBlueBike

setup_pipeline_logging()
logger = logging.getLogger(__name__)
engine = get_engine()

def pipeline():
    try:
        df = factBlueBike()
        report = validate_subset({"FactBlueBike": df}, ["FactBlueBike"])
        print_report(report)
        if not report.all_passed:
            logger.error("Validatie mislukt — FactBlueBike niet geladen naar DWH.")
            return
        loadIN(engine, df=df, table="FactBlueBike")
    except Exception as e:
        logger.exception("Fout in fillerBluebikeStation pipeline")

pipeline()
