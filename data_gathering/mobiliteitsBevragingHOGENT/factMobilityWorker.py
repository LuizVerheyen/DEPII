import json
import logging
from pathlib import Path
import sys

import pandas as pd

from DWH.connection.connect import getData,get_engine, loadIN
from data_gathering.hulp_functies import filterNewRows
from data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility import apply_metadata_labels

ROOT = Path(__file__).resolve().parents[2] # parents[2] gaat twee mappen omhoog vanaf hier
sys.path.append(str(ROOT))

logger = logging.getLogger(__name__)

engine = get_engine()

TRANSPORT_MAPPING = {
    "Te voet": "Te voet",
    "Fiets of elektrische fiets (speed pedelec inbegrepen)": "Fiets",
    "Trein": "Trein",
    "Bus, tram of metro": "Bus",
    "Wagen, bestelwagen of vrachtwagen alleen of met familieleden": "Auto",
    "Wagen, bestelwagen of vrachtwagen, met andere werknemers (op dezelfde of een andere vestigingseenheid tewerkgesteld)": "Auto",
    "Bromfiets of motorfiets": "Bromfiets",
    "Voertuigen van commerciële deelplatformen (bluebike, cambio, ...)": "Auto",
    "Step (al dan niet elektrisch), monowheel, hoverboard, enz.": "Step"
}

CO2_MAPPING = {
    "Te voet": 0.0,
    "Fiets": 0.0,
    "Step": 0.0,
    "Trein": 0.02000,
    "Bus": 0.03000,
    "Auto": 0.15000,
    "Bromfiets": 0.08000,   # zelf bepaalde waarde (pas aan indien nodig)
}

def ensure_transport_types(df):
    existing = getData(engine, "SELECT VehicleType FROM DimTransportType")
    existing_set = set(existing["VehicleType"].str.strip())
    new_types = set(df["TravelType"].dropna()) - existing_set
    if new_types:
        insert_rows = []
        for t in new_types:
            co2 = CO2_MAPPING.get(t, None)
            # fallback als mapping ontbreekt
            if co2 is None:
                co2 = 0.0
            insert_rows.append({
                "VehicleType": t,
                "CO2PerKM": co2
            })
        insert_df = pd.DataFrame(insert_rows)[["VehicleType", "CO2PerKM"]]
        loadIN(engine, df=insert_df, table="DimTransportType")

def factWorkerMobility():    
    file_path = ROOT / "data" / "DEPI_HOGENT_mobiliteitsbevraging_2024.csv"
    metadata_path = ROOT / "data" / "DEPI_meta_dict_HOGENT_mobiliteitsbevraging_2024.json"

    if not file_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden op: {file_path}")
    
    df = pd.read_csv(file_path, sep=";", encoding='unicode_escape')
    metadata_raw = open(metadata_path, "r", encoding="utf-8")
    metadata = json.load(metadata_raw)["value_labels"]

    # Alleen relevante data bijhouden
    columns_to_keep = ['RecordedDate', 'ResponseId', 'pendeltijd', 'pendelafstand', 'vervoermiddel']
    df = df[columns_to_keep]

    # Schalen van numerieke data (zoals in originele script: /10)
    df['vervoermiddel'] = df['vervoermiddel'] / 10

    # Hernoemen kolommen
    df = df.rename(columns={
        'RecordedDate': 'RecordDate',
        'ResponseId': 'ResponseID',
        'pendeltijd': 'TravelTime',
        'pendelafstand': 'TravelDistance',
        'vervoermiddel': 'TravelType'
    })

    # metadata labels linken aan kolom
    df = apply_metadata_labels(df, metadata)

    # juiste vervoermiddelen
    df["TravelType"] = df["TravelType"].map(TRANSPORT_MAPPING)

    # Datumformaat aanpassen naar DateKey (YYYYMMDD)
    df['RecordDate'] = pd.to_datetime(df['RecordDate'], format='%d/%m/%Y %H:%M')

    df['RecordDate'] = df['RecordDate'].dt.strftime('%Y%m%d').astype(int)

    ensure_transport_types(df)
    
    mobility_df = df[["ResponseID", "RecordDate", "TravelType", "TravelTime", "TravelDistance"]].copy()

    dim_worker = getData(engine,query="SELECT WorkerID, ResponseID, RecordDate FROM DimWorkerMobility")
    dim_transport = getData(engine,"SELECT TransportKey, VehicleType, CO2PerKM FROM DimTransportType")

    fact_df = mobility_df.merge(
        dim_worker,
        how="left",
        on=["ResponseID", "RecordDate"]
    )

    fact_df = fact_df.merge(
        dim_transport,
        how="left",
        left_on="TravelType",
        right_on="VehicleType"
    )

    fact_df.rename(columns={"RecordDate" : "DateKey"},inplace=True)

    fact_df = filterNewRows(
        df=fact_df,
        table="FactWorkerMobility",
        key_cols=["WorkerID", "DateKey", "TransportKey"]
    )

    if fact_df.empty:
        logger.info("Geen nieuwe antwoorden met vervoersmiddel.")
        return fact_df

    fact_df["TotalEmission"] = (fact_df["TravelDistance"] * fact_df ["CO2PerKM"])

    fact_df = fact_df[["WorkerID", "DateKey", "TransportKey", "TravelTime", "TravelDistance", "TotalEmission"]]

    fact_df["WorkerID"] = fact_df["WorkerID"].astype("Int64")
    fact_df["DateKey"] = fact_df["DateKey"].astype("Int64")
    fact_df["TransportKey"] = fact_df["TransportKey"].astype("Int64")
    return fact_df