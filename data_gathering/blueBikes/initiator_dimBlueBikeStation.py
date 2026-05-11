import logging
import pandas as pd
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

ROOT = Path().resolve().parents[1] 
sys.path.append(str(ROOT))

from DWH.connection.connect import getData,get_engine
from data_gathering.hulp_functies import filterNewRows, getLocationKey

engine = get_engine()
def dimBlueBikeStation():
    try:
        df_bluebike = pd.read_json("https://api.blue-bike.be/v4/location/website")
    except Exception as e:
        logger.exception("Blue-bike API call mislukt")
        df_bluebike = pd.DataFrame()

    df_bluebike = df_bluebike[['id', 'name', 'latitude', 'longitude' ]]
    df_bluebike.rename(columns={
        'id' : 'BlueBikeStationKey',
        'name' : 'LocationName',
        'latitude' : 'Latitude',
        'longitude' : 'Longitude'
    }, inplace=True)

    # Controleer welke stations nog niet in de dim zitten
    df_nieuw = filterNewRows(df=df_bluebike, table="DimBlueBikeStation", key_cols="BlueBikeStationKey")

    if df_nieuw.empty:
        logger.info("Geen nieuwe Blue-bike stations gevonden.")
        return df_nieuw

    logger.info("Nieuwe Blue-bike stations gevonden: %s", df_nieuw['BlueBikeStationKey'].tolist())
    logger.info("Start ophalen geodata voor %d locaties...", len(df_nieuw))

    for index, row in df_nieuw.iterrows():
        logger.debug("[%d/%d]", index + 1, len(df_nieuw))
        lat, lon = row['Latitude'], row['Longitude']
        locatieNaam = row['LocationName']

        location_key = getLocationKey(lat=lat, lon=lon, locatieNaam=locatieNaam)
        df_nieuw.at[index,'LocationKey'] = location_key

    return df_nieuw