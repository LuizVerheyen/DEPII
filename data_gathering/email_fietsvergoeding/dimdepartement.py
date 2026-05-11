from datetime import datetime
import logging

import pandas as pd
import sys
from pathlib import Path

from data_gathering.hulp_functies import filterNewRows, get_date_key

# Bepaal de ROOT (map 'dep')
ROOT = Path(__file__).resolve().parents[2] 
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
    

# Nu pas de import doen
from DWH.connection.connect import getData, get_engine

logger = logging.getLogger(__name__)

engine = get_engine()

def dimDepartement():
    df_departement = pd.read_excel(ROOT / "data" / "20260209_Veerle_Depestele_Aantallen_per_Entiteit.xlsx")

    df_departement.rename(columns={
            'Entiteit': 'DepartementName',
            'aantal': 'AmountOfWorkers',
            'JAAR': 'Year',
            'MAAND': 'Month'
        }, inplace=True)

    df_departement['StartDate'] = get_date_key(datetime.now())
    df_departement['EndDate'] = 20261231

    df_departement = filterNewRows(df_departement, 'DimDepartement', 'DepartementName')
    return df_departement[["DepartementName", "StartDate", "EndDate"]].drop_duplicates().copy()


def factDepartement():
    """
    df_departement: DataFrame met kolommen ['JAAR', 'MAAND', 'Entiteit', 'aantal']
    engine: SQLAlchemy engine om DimDepartement op te halen
    """

    df_departement = pd.read_excel(ROOT / "data" / "20260209_Veerle_Depestele_Aantallen_per_Entiteit.xlsx")

    df_departement.rename(columns={
            'Entiteit': 'DepartementName',
            'aantal': 'AmountOfWorkers',
            'JAAR': 'Year',
            'MAAND': 'Month'
        }, inplace=True)
        
    # 1. Haal de DimDepartement keys op
    df_dim = getData(engine, query="SELECT DepartementKey, DepartementName FROM DimDepartement")

    # 3. Merge met DimDepartement om DepartementKey te krijgen
    df_merged = pd.merge(
        df_departement,
        df_dim,
        on='DepartementName',
        how='left'
    )

    # 4. Voeg DateKey toe (YYYYMM01)
    df_merged['DateKey'] = df_merged['Year'] * 10000 + df_merged['Month'] * 100 + 1

    df_merged = filterNewRows(
        df=df_merged,
        table="FactDepartement",
        key_cols=["DateKey", "DepartementKey"]
    )

    if df_merged.empty:
        logger.info("Geen nieuwe departementen.")
        return df_merged[['DateKey', 'DepartementKey', 'AmountOfWorkers']]

    # 5. Return alleen de kolommen voor de fact tabel
    return df_merged[['DateKey', 'DepartementKey', 'AmountOfWorkers']]
