import logging
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

logger = logging.getLogger(__name__)

from data_gathering.telpalen.telpalen_aantal_fietsers import haal_all_counts

ROOT = Path().resolve().parents[1]
sys.path.append(str(ROOT))

from DWH.connection.connect import deleteData, get_engine, getData, loadIN

engine = get_engine()

# Aantal telpalen dat per DB-write gebundeld wordt.
# Hogere waarde = minder roundtrips, meer RAM gebruik.
BATCH_SIZE = 50


def fillFactCountings(load_to_db=True):
    logger.info("FactCountings aanvullen met nieuwe data")

    dim_countingpoint = getData(engine, query="SELECT * FROM DimCountingPoint")
    if dim_countingpoint is None or dim_countingpoint.empty:
        logger.warning("DimCountingPoint is leeg. Voer eerst dimCountingPoint.py uit.")
        return pd.DataFrame()

    # Verwijder huidige maand als er al data is (wordt opnieuw opgehaald)
    huidig_jaar   = datetime.today().year
    huidige_maand = datetime.today().month
    maand_str     = f"{huidig_jaar}{str(huidige_maand).zfill(2)}"

    bestaande = getData(engine, query=f"SELECT COUNT(*) AS aantal FROM FactCountings WHERE DateKey LIKE '{maand_str}%'")
    if bestaande["aantal"].iloc[0] > 0:
        pids = ", ".join(str(int(p)) for p in dim_countingpoint["CountingPointID"])
        deleteData(engine, query=f"DELETE FROM FactCountings WHERE CountingPointID IN ({pids}) AND DateKey LIKE '{maand_str}%'")

    totaal        = 0
    batch_buffer  = []   # tijdelijke buffer voor batch writes
    all_rows      = []   # alleen gevuld als load_to_db=False (voor validatie)

    def _flush_buffer(buffer):
        """Schrijf gebufferde batch in één keer naar de DB."""
        if not buffer:
            return
        df_bulk = pd.concat(buffer, ignore_index=True)
        loadIN(engine, df=df_bulk, table="FactCountings")
        buffer.clear()

    for df_batch in haal_all_counts(dim_countingpoint, engine=engine):
        df_batch["DateKey"] = df_batch["Date"].dt.strftime("%Y%m%d").astype(int)
        fact_batch = df_batch[[
            "CountingPointID", "DateKey",
            "DirectionInCounts", "DirectionOutCounts", "TotalCounts"
        ]].copy()
        fact_batch = fact_batch.astype({
            "CountingPointID":    int,
            "DateKey":            int,
            "DirectionInCounts":  int,
            "DirectionOutCounts": int,
            "TotalCounts":        int,
        })

        totaal += len(fact_batch)

        if load_to_db:
            batch_buffer.append(fact_batch)
            # Schrijf naar DB zodra de buffer vol genoeg is
            if len(batch_buffer) >= BATCH_SIZE:
                _flush_buffer(batch_buffer)
        else:
            all_rows.append(fact_batch)

    # Resterende rijen in de buffer wegschrijven
    if load_to_db:
        _flush_buffer(batch_buffer)

    logger.info("%d nieuwe rijen toegevoegd aan FactCountings.", totaal)

    # MODE 2: return voor validator
    if not load_to_db:
        return pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()

    return None