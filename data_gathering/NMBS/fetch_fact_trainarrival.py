import logging
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from DWH.connection.connect import getData, get_engine
from data_gathering.hulp_functies import get_date_key, get_datetime_from_unix, get_time_key, timekey_datekey_to_datetime

BASE_URL = "https://api.irail.be/liveboard/"
engine = get_engine()
def get_actual_arrival(row) -> datetime:
    planned_dt = timekey_datekey_to_datetime(row['DateKey'], row['TimeKey'])
    return planned_dt + timedelta(seconds=int(row['Delay']))

def round_down_30(dt: datetime) -> datetime:
    if dt.minute < 30:
        return dt.replace(minute=0, second=0, microsecond=0)
    else:
        return dt.replace(minute=30, second=0, microsecond=0)

def fetch_and_upsert_staging():
    NOW = datetime.now()
    DATE_API = NOW.strftime('%d%m%y')
    logger.info("TrainArrival fetch gestart: %s", NOW.strftime('%Y-%m-%d %H:%M'))

    df_stations = getData(engine, query="SELECT * FROM DimStation")
    records = []

    for _, row in df_stations.iterrows():
        params = {
            'id'    : row['URI'],
            'arrdep': 'arrival',
            'format': 'json',
            'date'  : DATE_API,
            'time'  : NOW.strftime('%H%M'),
        }
        try:
            arrivals = (
                requests.get(BASE_URL, params=params, timeout=10)
                .json()
                .get('arrivals', {})
                .get('arrival', [])
            )
        except Exception as e:
            logger.exception("Fout bij ophalen aankomsten voor %s", row['StationName'])
            arrivals = []

        for arrival in arrivals:
            arrival_dt = get_datetime_from_unix(int(arrival['time']))
            records.append({
                'TrainID'    : arrival['vehicle'],
                'StationKey' : row['StationKey'],
                'DateKey'    : get_date_key(arrival_dt),
                'TimeKey'    : get_time_key(arrival_dt),
                'Delay'      : int(arrival['delay']),
                'Canceled'   : arrival['canceled'] == '1',
                'LastUpdated': NOW,
            })
        logger.debug("  %s: %d aankomsten", row['StationName'], len(arrivals))
        time.sleep(0.2)

    if not records:
        logger.warning("Geen treinaankomsten opgehaald.")
        return None

    df_new = pd.DataFrame(records)
    pk = ['TrainID', 'StationKey', 'DateKey', 'TimeKey']

    # Upsert: verwijder oude versies van rijen die we gaan updaten, voeg nieuwe toe
    df_staging = getData(engine, query="SELECT * FROM stg_FactTrainArrival")
    if not df_staging.empty:
        df_staging = (
            df_staging
            .merge(df_new[pk], on=pk, how='left', indicator=True)
            .query("_merge == 'left_only'")
            .drop(columns='_merge')
        )

    df_upserted = pd.concat([df_staging, df_new], ignore_index=True)
    logger.info("Staging geüpdatet: %d rijen totaal", len(df_upserted))
    return df_upserted


def promote_stable_to_fact():
    NOW = datetime.now()
    cutoff = NOW - timedelta(hours=1, minutes=30)

    df_staging = getData(engine, query="SELECT * FROM stg_FactTrainArrival")
    if df_staging.empty:
        logger.info("Staging is leeg.")
        return None

    df_staging['ActualArrival'] = df_staging.apply(get_actual_arrival, axis=1)
    df_staging['StartTime'] = df_staging['ActualArrival'].apply(round_down_30)
    df_staging['DateKey_start'] = df_staging['StartTime'].apply(get_date_key)
    df_staging['StartTimeKey'] = df_staging['StartTime'].apply(get_time_key)

    # Bepaal per tijdvenster of ALLE treinen stabiel zijn
    df_staging['IsStable'] = (
        (df_staging['ActualArrival'] < cutoff) &
        (df_staging['LastUpdated'] < cutoff)
    )

    # Een tijdvenster mag pas naar de fact table als alle treinen erin stabiel zijn
    venster_stabiel = (
        df_staging
        .groupby(['DateKey_start', 'StartTimeKey'])['IsStable']
        .all()  # True alleen als elke rij in het venster stabiel is
        .reset_index()
        .rename(columns={'IsStable': 'VensterStabiel'})
    )

    # Koppel terug aan staging
    df_staging = df_staging.merge(
        venster_stabiel, on=['DateKey_start', 'StartTimeKey'], how='left'
    )
    df_klaar = df_staging[df_staging['VensterStabiel'] == True].copy()
    df_remaining  = df_staging[df_staging['VensterStabiel'] == False].copy()

    if df_klaar.empty:
        logger.info("Geen volledig stabiele tijdvensters om te promoveren.")
        return None

    df_klaar['EndTime'] = df_klaar['StartTime'] + timedelta(minutes=30)
    df_klaar['EndTimeKey'] = df_klaar['EndTime'].apply(get_time_key)

    # Alleen niet-geannuleerde treinen tellen mee voor AmountOfArrivals
    df_to_count = df_klaar[df_klaar['Canceled'] == False].copy()

    #.groupby() maakt de groepen, .size() telt het aantal rijen per groep, en .reset_index(name='AmountOfArrivals') zet het resultaat terug naar een gewone dataframe met AmountOfArrivals als kolomnaam.
    df_counts = (
        df_to_count
        .groupby(['StationKey', 'DateKey_start', 'StartTimeKey', 'EndTimeKey'])
        .size()
        .reset_index(name='AmountOfArrivals')
    )

    df_stations = getData(engine, query="SELECT StationKey FROM DimStation")
    stabiele_vensters = df_klaar[['DateKey_start', 'StartTimeKey', 'EndTimeKey']].drop_duplicates()

    df_fact = (
        df_stations
        .merge(stabiele_vensters, how='cross')
        .merge(df_counts, on=['StationKey', 'DateKey_start', 'StartTimeKey', 'EndTimeKey'], how='left')
        .fillna({'AmountOfArrivals': 0})
        .rename(columns={
            'DateKey_start' : 'DateKey',
            'StartTimeKey'  : 'StartTime',
            'EndTimeKey'    : 'EndTime'
        })
    )

    # Stabiele rijen verwijderen uit staging (zowel canceled als niet-canceled)
    df_remaining = df_remaining.drop(
        columns=['ActualArrival', 'StartTime', 'DateKey_start', 'StartTimeKey', 'IsStable', 'VensterStabiel']
    )
    
    logger.info("%d tijdvensters geladen in FactTrainArrival", len(df_fact))
    logger.info("Staging opgeschoond: %d rijen resterend", len(df_remaining))

    return df_fact, df_remaining