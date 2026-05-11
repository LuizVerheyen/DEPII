import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

from DWH.connection.connect import getData, get_engine
from data_gathering.hulp_functies import check_distance, get_date_key, get_time_key

engine = get_engine()

def factBlueBike():
    NOW      = datetime.now()
    DATE_KEY = get_date_key(NOW)
    TIME_KEY = get_time_key(NOW)

    logger.info("FactBlueBike fetch gestart: %s → DateKey=%d, TimeKey=%d", NOW.strftime('%Y-%m-%d %H:%M'), DATE_KEY, TIME_KEY)

    try:
        df_fact = pd.read_json("https://api.blue-bike.be/v4/location/website")
    except Exception as e:
        logger.exception("Blue-bike website API call mislukt")

    df_fact = df_fact[['id', 'total_bikes_available', 'e_bikes_available', 'blue_bikes_available', 'max_capacity', 'bikes_defect']]
    df_fact.rename(columns={
        'id' : 'BlueBikeStationKey',
        'total_bikes_available' : 'TotalBikesAvailable',
        'e_bikes_available' : 'EBikesAvailable',
        'blue_bikes_available' : 'BlueBikesAvailable',
        'max_capacity' : 'MaxCapacity',
        'bikes_defect' : 'BikesDefect'
    }, inplace=True)

    # BikesInUse ophalen uit de publieke API en toevoegen
    try:
        df_bluebike = pd.read_json("https://api.blue-bike.be/pub/location")
        df_bluebike = df_bluebike[['id', 'bikes_in_use']]
        df_bluebike.rename(columns={
            'id': 'BlueBikeStationKey',
            'bikes_in_use': 'BikesInUse'
        }, inplace=True)
    except Exception as e:
        logger.exception("Blue-bike publieke API call mislukt")
        df_bluebike = pd.DataFrame(columns=['BlueBikeStationKey', 'BikesInUse'])
    
    df_fact = df_fact.merge(df_bluebike, on='BlueBikeStationKey', how='left')

    # 'isin' zou altijd moeten kloppen behalve als er een nieuwe bluebike locatie is en de dim is niet geupdate
    df_dimBlueBikeStation = getData(engine, query="SELECT * FROM DimBlueBikeStation")
    df_fact = df_fact[df_fact['BlueBikeStationKey'].isin(df_dimBlueBikeStation['BlueBikeStationKey'])]

    df_fact['DateKey'] = DATE_KEY
    df_fact['TimeKey'] = TIME_KEY

    df_dimStation = getData(engine, query="SELECT * FROM DimStation")

    # Haal lat/lon op van de BlueBike stations voor de afstandsberekening
    df_fact = df_fact.merge(
        df_dimBlueBikeStation[['BlueBikeStationKey', 'Latitude', 'Longitude']],
        on='BlueBikeStationKey',
        how='left'
    )
    df_fact['LinkedStationKey'] = get_linked_station_key(df_fact, df_dimStation)
    
    # Lat/lon weer verwijderen want die horen niet in de fact tabel
    df_fact.drop(columns=['Latitude', 'Longitude'], inplace=True)
    
    return df_fact


def get_linked_station_key(df_bluebike, df_stations, max_distance_m=500):
    linked = []
    for _, bike_row in df_bluebike.iterrows():
        best_key = None
        best_dist = float('inf')
        for _, station_row in df_stations.iterrows():
            dist = check_distance(
                bike_row['Latitude'], bike_row['Longitude'],
                station_row['Latitude'], station_row['Longitude']
            )
            if dist < best_dist:
                best_dist = dist
                best_key = station_row['StationKey']
        if best_dist <= max_distance_m:
            linked.append(best_key)
        else:
            linked.append(None)
    return linked