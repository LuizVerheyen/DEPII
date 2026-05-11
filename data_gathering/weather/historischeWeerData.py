import logging
import pandas as pd
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


ROOT = Path.cwd()
while ROOT != ROOT.parent and not (ROOT / 'DWH').exists():
    ROOT = ROOT.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
    
    
from DWH.connection.connect import loadIN, get_engine

engine = get_engine()

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

df = pd.read_csv(ROOT / "data" / "weatherData" / "aws_1day" / "historische_data_2010-01-01-2026-03-28.csv")

df.rename(columns={
    "code": "WeatherStationKey",
    "timestamp": "DateKey",
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

df.drop(columns=['fid', 'the_geom', 'qc_flags', 'FID'], inplace=True, errors='ignore')
df['DateKey'] = pd.to_datetime(df['DateKey']).dt.strftime('%Y%m%d').astype(int)

for col in NON_NEGATIVE_METEO_COLUMNS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        negative_count = (df[col] < 0).sum()
        if negative_count > 0:
            logger.info("%d negatieve waarde(n) in %s gecorrigeerd naar 0", negative_count, col)
        df[col] = df[col].clip(lower=0)

logger.info("Historische weerdata geladen: %d rijen", len(df))

loadIN(engine, df=df, table='FactMeteo')
