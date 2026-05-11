import logging
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

def fetch_and_load_fact_nmbs(server="Local"):
    """
    Haalt stations op uit DimStation, ophaalt live data van iRail,
    en laadt dit in FactNMBS.
    """
    load_dotenv()
    
    # 1. Database Connectie Setup
    conn_str = os.getenv("db_lokaal_conn" if server.lower() == 'local' else "df_VIC_conn")
    if not conn_str:
        raise ValueError("Database connection string niet gevonden in .env")
        
    engine = create_engine(conn_str)
    BASE_URL = 'https://api.irail.be/liveboard/'
    
    # 2. Station Data ophalen uit DB
    query_stations = "SELECT StationKey, URI, StationName FROM DimStation"
    with engine.connect() as conn:
        df_stations = pd.read_sql(text(query_stations), conn)

    if df_stations.empty:
        logger.warning("Geen stations gevonden in DimStation.")
        return pd.DataFrame()

    # 3. Datum instellingen
    NOW = datetime.now()
    DATE_KEY = int(NOW.strftime('%Y%m%d'))
    DATE_API = NOW.strftime('%d%m%y')
    
    records = []

    # 4. Data ophalen via iRail API
    for _, row in df_stations.iterrows():
        station_key = row['StationKey']
        uri         = row['URI']
        station_name = row['StationName']

        call_time  = datetime.now().replace(second=0, microsecond=0)
        start_time = call_time
        end_time   = start_time + timedelta(minutes=30)

        params = {
            'id'     : uri,
            'station': station_name,
            'arrdep' : 'arrival',
            'format' : 'json',
            'date'   : DATE_API,
            'time'   : start_time.strftime('%H%M')
        }

        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            all_arrivals = data.get('arrivals', {}).get('arrival', [])

            # Filter op timeslot en annuleringen
            arrivals_in_timeslot = [
                arrival for arrival in all_arrivals
                if (
                    start_time.timestamp() <= int(arrival['time']) + int(arrival['delay']) < end_time.timestamp()
                    and arrival['canceled'] == '0'
                )
            ]

            records.append({
                'DateKey'      : DATE_KEY,
                'TimeKey'      : int(start_time.strftime('%H%M')),
                'StationKey'   : station_key,
                'TotalArrivals': len(arrivals_in_timeslot)
            })

            logger.debug("Verwerkt: %s - %d aankomsten", station_name, len(arrivals_in_timeslot))

        except Exception as e:
            logger.exception("Fout bij ophalen aankomsten voor %s", station_name)

    # 5. Data laden in FactNMBS
    if records:
        df_fact = pd.DataFrame(records)
        
        # Data naar SQL schrijven
        logger.info("%d records geladen in FactNMBS.", len(df_fact))
        
        return df_fact
    else:
        logger.warning("Geen treindata opgehaald.")
        return pd.DataFrame()
