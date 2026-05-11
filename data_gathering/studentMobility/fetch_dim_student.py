import logging
import pandas as pd
from pathlib import Path
import sys

from data_gathering.hulp_functies import filterNewRows

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2] 
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from DWH.connection.connect import get_engine, getData

engine = get_engine()

def fillDimStudent():
    df_student = pd.read_excel(ROOT / "data" / "Registratie vervoermiddel studenten DEPI.xlsx")

    df_student = df_student.rename(columns={
        "Naam": "StudentName"
    })

    df_student["StudentName"] = df_student["StudentName"].str.strip()
    df_student = df_student[["StudentName"]].drop_duplicates()

    df_student["DepartementName"] = "DIT"

    dim_depart = getData(engine, "SELECT DepartementKey, DepartementName FROM DimDepartement")

    df_student = df_student.merge(dim_depart, on="DepartementName", how="left")

    df_student = df_student[["StudentName", "DepartementKey"]]
    df_student.dropna(subset="StudentName", inplace=True)

    df_student = filterNewRows(
        df=df_student,
        table="DimStudent",
        key_cols="StudentName",
    )

    if df_student.empty:
        logger.info("Geen nieuwe studenten gevonden.")
        return df_student

    return df_student