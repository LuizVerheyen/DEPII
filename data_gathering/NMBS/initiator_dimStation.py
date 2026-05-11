import logging
import pandas as pd

from DWH.connection.connect import getData, get_engine

logger = logging.getLogger(__name__)
from data_gathering.hulp_functies import check_distance, filterNewRows, getLocationKey

engine = get_engine()
def dimStation(dim_BlueBike=None):
    df_stations = pd.read_csv('https://raw.githubusercontent.com/iRail/stations/refs/heads/master/stations.csv')
    if dim_BlueBike is None or dim_BlueBike.empty:
        dim_BlueBike = getData(engine, query="SELECT * FROM DimBlueBikeStation")
    df_stations['URI'] = df_stations['URI'].str.replace('http://irail.be/stations/NMBS/', '', regex=False)
    cross = dim_BlueBike.merge(df_stations, how="cross")
    cross['afstand_m'] = check_distance(
        cross['Latitude'], cross['Longitude'],
        cross['latitude'], cross['longitude']
    )

    cross['binnen_500m'] = cross['afstand_m'] <= 500

    # blue bike plaatsen bij een station
    df_bluebike_bij_station = (cross[cross['binnen_500m']][['URI', 'name', 'latitude', 'longitude']]).copy()
    df_bluebike_bij_station.rename(columns={
        'name'     : 'StationName',
        'latitude' : 'Latitude',
        'longitude': 'Longitude',
    }, inplace=True)

    dim_station = df_bluebike_bij_station.drop_duplicates().reset_index(drop=True).copy()

    dim_station = filterNewRows(df=dim_station, table="DimStation", key_cols="URI")

    if dim_station.empty:
        logger.info("Geen nieuwe stations gevonden.")
        return dim_station

    logger.info("Start ophalen geodata voor %d NMBS-stations...", len(dim_station))

    for index, row in dim_station.iterrows():
        logger.debug("[%d/%d]", index + 1, len(dim_station))
        lat, lon = row['Latitude'], row['Longitude']
        locatieNaam = row['StationName']

        location_key = getLocationKey(lat=lat, lon=lon, locatieNaam=locatieNaam)
        dim_station.at[index,'LocationKey'] = location_key

    return dim_station
