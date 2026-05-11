# %% [markdown]
# # Weerdata AWS_1DAY
# 
# - We halen de data op via de URL (netwerk) en geven de nodige parameters mee. 
#   - de URL is te zien bij het netwerk
# - Dit script dient elke dag te laden zodat data automatisch wordt geladen in de database (elke dag om 23:59:59)

# %%
import logging
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
from pathlib import Path
import sys

from data_gathering.hulp_functies import filterNewRows

logger = logging.getLogger(__name__)

ROOT = Path().resolve().parents[1] 
sys.path.append(str(ROOT))


# %%
BASE_URL = "https://opendata.meteo.be/service/ows"

NON_NEGATIVE_METEO_COLUMNS = [
    "PrecipQuantity",
    "WindSpeed10m",
    "WindSpeedAvg30m",
    "WindGustsSpeed",
    "HumidityRelShelterAvg",
    "Pressure",
    "SunDuration",
    "ShortWaveFromSkyAvg",
    "SunIntAvg",
]


# %% [markdown]
# !["../../images/weather_BASE_URL.png"](attachment:image.png)

# %%
def download_weather_for_date():
    date = datetime.now() - timedelta(days=1)
    start = date.strftime("2010-01-01 00:00:00")
    end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    date_str = date.date()
    
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": "aws:aws_1day",
        "outputformat": "text/csv",
        "CQL_FILTER": f"timestamp between '{start}' AND '{end}'"
    }

    logger.info("Ophalen weerdata voor %s", date_str)

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        
        if not response.text.strip():
            logger.warning("Geen data gevonden voor %s", date_str)
            return None

        df = pd.read_csv(io.StringIO(response.text))
        
        # 1. DateKey en TimeKey aanmaken VOORDAT we de timestamp droppen
        if 'timestamp' in df.columns:
            # Zet om naar datetime object
            temp_ts = pd.to_datetime(df['timestamp'])
            df['DateKey'] = temp_ts.dt.strftime('%Y%m%d').astype(int)
        
        # 2. Opschonen van originele API kolommen
        cols_to_drop = ['FID', 'qc_flags', 'the_geom', 'timestamp']
        df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
        
        # 3. Kolommen hernoemen naar PascalCase conform SQL tabel
        df.rename(columns={
            "code": "WeatherStationKey",
            "precip_quantity": "PrecipQuantity",
            "temp_avg": "TempAvg",
            "temp_max": "TempMax",
            "temp_min": "TempMin",
            "temp_grass_pt100_avg": "TempGrassPt100Avg",
            "temp_soil_avg": "TempSoilAvg",
            "temp_soil_avg_5cm": "TempSoilAvg5cm",
            "temp_soil_avg_10cm": "TempSoilAvg10cm",
            "temp_soil_avg_20cm": "TempSoilAvg20cm",
            "temp_soil_avg_50cm": "TempSoilAvg50cm",
            "wind_speed_10m": "WindSpeed10m",
            "wind_speed_avg_30m": "WindSpeedAvg30m",
            "wind_gusts_speed": "WindGustsSpeed",
            "humidity_rel_shelter_avg": "HumidityRelShelterAvg",
            "pressure": "Pressure",
            "sun_duration": "SunDuration",
            "short_wave_from_sky_avg": "ShortWaveFromSkyAvg",
            "sun_int_avg": "SunIntAvg"
        }, inplace=True)

        # Kleine negatieve sensorafwijkingen op fysisch niet-negatieve metingen
        # normaliseren naar 0 zodat validatie en DDL-checks niet falen.
        for col in NON_NEGATIVE_METEO_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    logger.info("%d negatieve waarde(n) in %s gecorrigeerd naar 0", negative_count, col)
                df[col] = df[col].clip(lower=0)
        
        df = filterNewRows(
            df=df,
            table="FactMeteo",
            key_cols=["DateKey", "WeatherStationKey"],
        )

        if df.empty:
            logger.info("Geen nieuwe weer gevonden.")
            return df

    except Exception as e:
        logger.exception("Fout bij ophalen weerdata voor %s", date_str)
        return None

    logger.info("Weerdata geladen voor %s: %d rijen", date_str, len(df))
    return df

