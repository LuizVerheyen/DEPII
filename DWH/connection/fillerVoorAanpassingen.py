import logging
import os
import sys

_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_pipeline_logging
from DWH.connection.connect import loadIN, get_engine
from DWH.connection.validator import validate_subset, print_report
from data_gathering.weather.initializer import download_weather_for_date

setup_pipeline_logging()
logger = logging.getLogger(__name__)
engine = get_engine()

def pipeline():
    try:
        df = download_weather_for_date()
        report = validate_subset({"FactMeteo": df}, ["FactMeteo"])
        print_report(report)
        if not report.all_passed:
            logger.error("Validatie mislukt — FactMeteo niet geladen naar DWH.")
            return
        loadIN(engine, df=df, table='FactMeteo')
    except Exception as e:
        logger.exception("Fout in fillerVoorAanpassingen pipeline")

pipeline()
