import logging
import pandas as pd
from pathlib import Path
import sys

from data_gathering.hulp_functies import filterNewRows

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2] 
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from DWH.connection.connect import get_engine, getData, loadIN

engine = get_engine()

# Zorgt ervoor dat alle transporttypes bestaan in DimTransportType.
def ensure_transport_types(engine, df):
    dim = getData(engine, "SELECT VehicleType FROM DimTransportType")

    existing = set(dim["VehicleType"].str.strip())

    new_types = set(df["TransportType"].dropna().unique()) - existing

    if new_types:
        logger.info("Nieuwe transporttypes gevonden: %s", new_types)

        new_df = pd.DataFrame({
            "VehicleType": list(new_types),
            "CO2PerKM": 0.0  # default fallback
        })

        loadIN(engine, df=new_df, table="DimTransportType")
        logger.info("DimTransportType aangevuld.")

def validate_datekey_with_dim(engine, df):
    dim_dates = getData(engine, "SELECT DateKey FROM DimDate")
    valid_dates = set(dim_dates["DateKey"])

    df = df[df["DateKey"].isin(valid_dates)]

    return df

def fillFactStudentMobility():
    df = pd.read_excel(ROOT / "data" / "Registratie vervoermiddel studenten DEPI.xlsx")

    # Rename columns to match expected names
    df = df.rename(columns={
        "Naam": "StudentName",
        "Begintijd": "DateKey",  # Use Begintijd as the date column
        "Km": "DistanceKM",
        "Vervoermiddel": "TransportType"
    })

    # Convert datetime to DateKey format (YYYYMMDD)
    df["DateKey"] = pd.to_datetime(df["DateKey"]).dt.strftime("%Y%m%d").astype(int)

    df = df[["StudentName", "DateKey", "TransportType", "DistanceKM"]]

    df["StudentName"] = df["StudentName"].str.strip()
    df["TransportType"] = df["TransportType"].str.strip()
    df = validate_datekey_with_dim(engine, df)

    mapping = {
        "Openbaar vervoer - trein": "Trein",
        "Openbaar vervoer - bus": "Bus",
        "Openbaar vervoer - tram": "Trein",
        "Fiets": "Fiets",
        "Te voet": "Te voet",
        "Elektrische fiets / step": "Fiets",
        "Elektrische wagen": "Auto",
        "Auto": "Auto"
    }

    df["TransportType"] = df["TransportType"].map(mapping)

    df = df.dropna(subset=["TransportType"])
    df = df.dropna(subset=["StudentName"])

    ensure_transport_types(engine, df)

    # DimStudent ophalen
    dim_student = getData(engine, "SELECT StudentKey, StudentName FROM DimStudent")
    dim_student["StudentName"] = dim_student["StudentName"].str.strip()

    # DimTransport ophalen
    dim_transport = getData(engine, "SELECT TransportKey, VehicleType FROM DimTransportType")

    df = df.merge(dim_student, on="StudentName", how="left")
    df = df.merge(dim_transport, left_on="TransportType", right_on="VehicleType", how="left")

    df = filterNewRows(
        df=df,
        table="FactStudentMobility",
        key_cols=["StudentKey", "DateKey", "TransportKey"],
    )

    if df.empty:
        logger.info("Geen nieuwe antwoorden gevonden.")
        return df[["StudentKey", "DateKey", "TransportKey", "DistanceKM"]]

    return df[["StudentKey", "DateKey", "TransportKey", "DistanceKM"]]