import logging
import os
import sys

from DWH.connection.validator import print_report, validate_subset

_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_pipeline_logging
from DWH.connection.connect import loadIN, get_engine
from data_gathering.NMBS.fetch_fact_trainarrival import fetch_and_upsert_staging, promote_stable_to_fact

setup_pipeline_logging()
logger = logging.getLogger(__name__)
engine = get_engine()

def pipeline():
    try:
        loadIN(engine, df=fetch_and_upsert_staging(), table='stg_FactTrainArrival', if_exists='replace')
        result = promote_stable_to_fact()
        if result is None:
            logger.info("Niets te promoveren.")
            return
        df_fact, df_remaining = result
        report = validate_subset({"FactTrainArrival": df_fact}, ["FactTrainArrival"])
        print_report(report)
        if not report.all_passed:
            logger.error("Validatie mislukt — FactTrainArrival niet geladen naar DWH.")
            return
        loadIN(engine, df=df_fact, table='FactTrainArrival')
        loadIN(engine, df=df_remaining, table='stg_FactTrainArrival', if_exists='replace')
    except Exception as e:
        logger.exception("Fout in fillerTrain pipeline")

pipeline()
