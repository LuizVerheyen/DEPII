import logging
import pandas as pd
from pathlib import Path
import sys

from DWH.connection.connect import get_engine, getData

logger = logging.getLogger(__name__)
from data_gathering.hulp_functies import getLocationKey
from data_gathering.telpalen.telpalen_locatie_fetcher import haal_telpalen_volledig_op
 
ROOT = Path().resolve().parents[1]
sys.path.append(str(ROOT))

engine = get_engine()

def fillDimCountingPoint():
    logger.info("DimCountingPoint opvullen")

    existing = getData(engine, "SELECT CountingPointID FROM DimCountingPoint")
    if existing is not None and not existing.empty:
        existing_ids = existing["CountingPointID"].tolist()
        # nieuwe telpalen ophalen
        df_telpalen = haal_telpalen_volledig_op(existing_ids=existing_ids)

    else:
        df_telpalen = haal_telpalen_volledig_op()

    if df_telpalen is None or df_telpalen.empty:
        logger.info("Geen nieuwe telpalen gevonden.")
        return pd.DataFrame()

    df_telpalen = df_telpalen.rename(columns={
        'counting_point_id' : 'CountingPointID',
        'customId'          : 'CustomID',
        'name'              : 'CountingPointName',
        'latitude'          : 'Latitude',
        'longitude'         : 'Longitude',
        'firstData'         : 'FirstData',
        'granularity'       : 'Granularity',
        'directional'       : 'Directional',
        'direction_name_in' : 'DirectionNameIn',
        'direction_name_out': 'DirectionNameOut',
        'domain_id'         : 'DomainID',
        'domain_name'       : 'DomainName',
        'description'       : 'Description',
    })

    df_telpalen["CountingPointID"] = df_telpalen["CountingPointID"].astype("Int64")

    # LocationKey opzoeken
    logger.info("LocationKeys ophalen voor %d telpalen", len(df_telpalen))
    for index, row in df_telpalen.iterrows():
        logger.debug("[%d/%d]", index + 1, len(df_telpalen))
        naam = str(row['CountingPointName'])
        lat, lon = row['Latitude'], row['Longitude']

        location_key = getLocationKey(lat=lat, lon=lon, locatieNaam=naam)
        df_telpalen.at[index,'LocationKey'] = location_key

    missing = df_telpalen["LocationKey"].isna().sum()
    if missing > 0:
        logger.warning("%d telpalen overgeslagen wegens ontbrekende LocationKey (API timeout).", missing)
        df_telpalen = df_telpalen.dropna(subset=["LocationKey"])

    df_telpalen["Directional"] = df_telpalen["Directional"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    dim_countingpoint = df_telpalen[[
        "CountingPointID", "CustomID", "CountingPointName",
        "Latitude", "Longitude", "FirstData",
        "Granularity", "Directional", "DirectionNameIn", "DirectionNameOut",
        "DomainID", "DomainName", "Description", "LocationKey",
    ]].copy()

    dim_countingpoint["CountingPointID"] = dim_countingpoint["CountingPointID"].astype(int)
    dim_countingpoint["Latitude"] = dim_countingpoint["Latitude"].astype(float)
    dim_countingpoint["Longitude"] = dim_countingpoint["Longitude"].astype(float)
    dim_countingpoint["LocationKey"] = dim_countingpoint["LocationKey"].astype(int)

    return dim_countingpoint
        
