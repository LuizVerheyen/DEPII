import logging
import requests
import pandas as pd
import io
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

import sys

from data_gathering.hulp_functies import filterNewRows, getLocationKey

ROOT = Path().resolve().parents[0] 
sys.path.append(str(ROOT))

load_dotenv()

# Basis setup
BASE_URL = "https://opendata.meteo.be/service/ows"

def download_aws_stations():
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": "aws:aws_station",
        "outputformat": "text/csv"
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))

        df["Latitude"] = df["the_geom"].str.replace("POINT (", "", regex=False).str.replace(")", "", regex=False).str.split().str[0].astype(float)
        df["Longitude"] = df["the_geom"].str.replace("POINT (", "", regex=False).str.replace(")", "", regex=False).str.split().str[1].astype(float)
        df['Point'] = df['the_geom'].str.replace("POINT ", "", regex=False)

        df.rename(columns={
            "code": "WeatherStationID",
            "name": "Name",
            "altitude": "Altitude",
            "province": "Province"
        }, inplace=True)

        df = filterNewRows(
            df=df,
            table="DimWeatherStation",
            key_cols="WeatherStationID"
        )

        if df.empty:
            logger.info("Geen nieuwe weerstations gevonden.")
            return df[["WeatherStationID", "Name", "Altitude", "Latitude", "Longitude", "Point"]]

        for index, row in df.iterrows():
            logger.debug("[%d/%d]", index + 1, len(df))
            naam = str(row['Name'])
            lat, lon = row['Latitude'], row['Longitude']
            location_key = getLocationKey(lat=lat, lon=lon, locatieNaam=naam)
            df.at[index,'LocationKey'] = location_key

        df["SnapshotDate"] = pd.Timestamp.now().normalize().date()
        df['Altitude'] = pd.to_numeric(df['Altitude'], errors='coerce')
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        df['LocationKey'] = df['LocationKey'].astype("Int64")

        df = df[["WeatherStationID", "Name", "Altitude", "Latitude", "Longitude", "Point", "LocationKey", "SnapshotDate"]]

        print(df)

        return df
    except Exception as e:
        logger.exception("Fout bij downloaden van weerstations")
        return None
    
download_aws_stations()