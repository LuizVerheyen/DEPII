import logging
import pandas as pd
from pathlib import Path
import sys
import json

from data_gathering.hulp_functies import filterNewRows, getLocationKey

logger = logging.getLogger(__name__)

#Coordinaten belgie (ongeveer)
MIN_LAT=49.4 
MAX_LAT=51.6 
MIN_LON=2.5 
MAX_LON=6.5

# Zorg dat de root wordt gevonden, pas dit pad aan indien nodig
ROOT = Path(__file__).resolve().parents[2] # parents[2] gaat twee mappen omhoog vanaf hier
sys.path.append(str(ROOT))

COLUMN_LABEL_MAP = {
    "WorkPlace": "labels3",
    "TravelType": "labels4",
    "WorkFunction": "labels195",
    "WorkRegime": "labels7",
    "HomeWork": "labels8"
}

def corrigeer_lat(val):
    """Corrigeert afwijkende latitude formaten."""
    str_val = str(val).replace('.', '')
    # Verwijder '.0' indien aanwezig
    if str_val.endswith('0'):
        str_val = str_val[:-1]
    
    lengte = len(str_val)
    
    if lengte == 5: # Bijv. 51047
        return float(val) / 1000
    elif lengte == 6: # Bijv. 508852
        return float(val) / 10000
    else:
        return float(val)
    
def apply_metadata_labels(df, metadata):
    for col, label_key in COLUMN_LABEL_MAP.items():
        if col not in df.columns:
            continue
        if label_key not in metadata:
            continue
        mapping = {
            float(k): v
            for k, v in metadata[label_key].items()
        }
        df[col] = df[col].map(mapping)
    return df

def dimWM():
    # 1. Bestanden definiëren
    file_path = ROOT / "data" / "DEPI_HOGENT_mobiliteitsbevraging_2024.csv"
    metadata_path = ROOT / "data" / "DEPI_meta_dict_HOGENT_mobiliteitsbevraging_2024.json"

    # 2. Data inladen
    if not file_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden op: {file_path}")
    
    df = pd.read_csv(file_path, sep=";", encoding='unicode_escape')
    metadata_raw = open(metadata_path, "r", encoding="utf-8")
    metadata = json.load(metadata_raw)["value_labels"]

    # 3. Alleen relevante data bijhouden
    columns_to_keep = [
        'RecordedDate', 'ResponseId', 'LocationLatitude', 'LocationLongitude', 
        'werkplek', 'Finished', 'functie', 'werk__', 'thuiswerk'
    ]
    df = df[columns_to_keep]

    # 4. Lat/Lon correctie
    df['LocationLatitude'] = df['LocationLatitude'].apply(corrigeer_lat)
    df['LocationLongitude'] = df['LocationLongitude'] / 10000

    df["LocationKey"] = pd.NA 

    # 5. Hernoemen kolommen
    df = df.rename(columns={
        'RecordedDate': 'RecordDate',
        'ResponseId': 'ResponseID',
        'LocationLatitude': 'Latitude',
        'LocationLongitude': 'Longitude', 
        'werkplek': 'WorkPlace',
        "functie": "WorkFunction", 
        "werk__": "WorkRegime",
        'thuiswerk': "HomeWork"
    })

    df = filterNewRows(
        df=df,
        table="DimWorkerMobility",
        key_cols="ResponseID"
    )

    if df.empty:
        logger.info("Geen nieuwe Responses gevonden.")
        return df

    # 6. Geolocation data ophalen en LocationKey toevoegen
    for index, row in df.iterrows():
        logger.debug("[%d/%d]", index + 1, len(df))
        lat, lon = row['Latitude'], row['Longitude']
        if pd.isna(lat) or pd.isna(lon) or not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
            continue
        locationKey = getLocationKey(lat=lat, lon=lon)
        df.at[index,'LocationKey'] = locationKey

    df["LocationKey"] = df["LocationKey"].astype("Int64")    

    # 7. Schalen van numerieke data (zoals in originele script: /10)
    for i in df.columns[4:]: # Vanaf 'werkplek'
        if df[i].dtype in ['float64', 'int64']:
            df[i] = df[i] / 10    

    # 8. metadata labels linken aan kolom
    df = apply_metadata_labels(df, metadata)

    # 9. Datumformaat aanpassen naar DateKey (YYYYMMDD)
    df['RecordDate'] = pd.to_datetime(df['RecordDate'], format='%d/%m/%Y %H:%M')

    df['RecordDate'] = df['RecordDate'].dt.strftime('%Y%m%d').astype(int)
    
    return df[["ResponseID","RecordDate", "LocationKey", "Latitude", "Longitude", "WorkPlace", "WorkFunction", "WorkRegime", "HomeWork", "Finished"
    ]]
