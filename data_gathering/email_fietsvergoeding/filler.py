import logging
import pandas as pd
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

logger = logging.getLogger(__name__)

from DWH.connection.connect import getData
from DWH.connection.connect import get_engine
from data_gathering.email_fietsvergoeding.fetcher import fetch_and_process
from data_gathering.hulp_functies import filterNewRows

engine = get_engine()

# Module-level flag: zorgt dat fetch_and_process() maximaal één keer per
# process draait, ook al wordt _load_combined() meermaals aangeroepen
# (eenmaal door fillDimStaff, eenmaal door fillFactStaffCommute).
_email_fetch_done = False


def _ensure_emails_fetched() -> None:
    """Roept fetch_and_process() één keer per process aan."""
    global _email_fetch_done
    if _email_fetch_done:
        return
    try:
        fetch_and_process()
    except Exception as e:
        logger.warning("Email-fetcher faalde: %s — verder met bestaande data", e)
    _email_fetch_done = True


def _load_combined() -> pd.DataFrame:
    # Zorg dat emails_final.csv up-to-date is met de laatste Gmail-binnenkomers
    # voordat we ze samenvoegen met de fietsvergoedingen-CSV.
    _ensure_emails_fetched()

    df_fiet = pd.read_csv(
        ROOT / "data" / "fietsvergoedingen_personeel_HOGENT_2024_2025.csv", sep=";"
    ).rename(columns={
        "PersoneelsID":              "StaffID",
        "Entiteit":                  "Entity",
        "Hoofdcampus":               "Campus",
        "Postcode of postcode groep": "PostalCode",
        "totaal aantal km":          "DistanceKM",
        "periode":                   "Period",
    })

    # emails_final.csv bestaat pas zodra de fetcher de eerste geaccepteerde mail
    # heeft verwerkt. Als de file (nog) niet bestaat of leeg is → gewoon doorgaan
    # met enkel de fietsvergoedingen-data.
    emails_path = ROOT / "data" / "e-mails_fietsvergoeding" / "emails_final.csv"
    try:
        df_mail = pd.read_csv(emails_path, sep=";")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        logger.info("emails_final.csv bestaat (nog) niet — alleen fietsvergoedingen-CSV gebruikt.")
        df_mail = pd.DataFrame(columns=df_fiet.columns)

    combined = pd.concat([df_fiet, df_mail], ignore_index=True)

    # Drop kolommen die conflicteren met de melt verderop
    combined = combined.drop(columns=["DistanceKM", "PostalCode"], errors="ignore")

    return combined
def fillDimStaff() -> pd.DataFrame:
    df = _load_combined()
    dim_departement = getData(engine, query="SELECT DepartementKey, DepartementName FROM DimDepartement")

    df_result = df.merge(
        dim_departement,
        left_on="Entity",
        right_on="DepartementName",
        how="left"
    )

    result = (
        df_result[["StaffID", "DepartementKey", "Campus"]]
        .drop_duplicates(subset=["StaffID"])
    )

    # Skip personeelsleden die al in DimStaff zitten — voorkomt duplicate
    # StaffID-rijen bij herhaalde pipeline-runs.
    return filterNewRows(result, "DimStaff", ["StaffID"])


def fillFactStaffCommute() -> pd.DataFrame | None:
    df = _load_combined()

    # Surrogate keys ophalen (StaffID is nodig om te kunnen mergen op natural key)
    df_staff_db = getData(engine, query="SELECT StaffKey, StaffID FROM DimStaff")
    df_date_db  = getData(engine, query="SELECT DateKey, DayOfMonth, [Month], [Year] FROM DimDate")

    if isinstance(df_staff_db, Exception) or isinstance(df_date_db, Exception):
        logger.error("Fout bij ophalen database gegevens.")
        return None

    # Melt naar long formaat
    dag_kolommen = [f"dag {i}" for i in range(1, 32)]
    df_long = pd.melt(
        df,
        id_vars=["StaffID", "Period"],
        value_vars=dag_kolommen,
        var_name="Dag_Raw",
        value_name="DistanceKM"
    )

    # Cleaning
    df_long = df_long.dropna(subset=["DistanceKM"])
    df_long = df_long.dropna(subset=["Period"])
    df_long["DistanceKM"] = pd.to_numeric(
        df_long["DistanceKM"].astype(str).str.replace(',', '.'),
        errors='coerce'
    ).astype("Float64")
    df_long = df_long[df_long["DistanceKM"] > 0].copy()

    # Datum extractie - 'mar' toegevoegd voor Engelse afkorting in emails_final.csv
    maand_map = {
        'jan': 1, 'feb': 2, 'mrt': 3, 'mar': 3, 'apr': 4, 'mei': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
    }
    temp_date = df_long['Period'].str.split('/', expand=True)
    df_long['DayOfMonth'] = df_long["Dag_Raw"].str.extract(r"(\d+)").astype(int)
    df_long['Month'] = temp_date[0].str.lower().map(maand_map)
    df_long['Year']  = temp_date[1].apply(lambda x: 2000 + int(x))

    # Drop rijen waar Month niet kon worden gemapt (onbekende afkorting)
    df_long = df_long.dropna(subset=["Month"])
    df_long["Month"] = df_long["Month"].astype(int)

    # Type matching - merge op natural key (StaffID), niet op surrogate key
    df_long["StaffID"]     = df_long["StaffID"].astype(str)
    df_staff_db["StaffID"] = df_staff_db["StaffID"].astype(str)

    # Merges
    df_fact = df_long.merge(df_staff_db, on="StaffID", how="inner")
    df_fact = df_fact.merge(df_date_db, on=["DayOfMonth", "Month", "Year"], how="inner")

    # einde van fillFactStaffCommute, vervang de laatste twee regels door:
    final_fact = df_fact[["StaffKey", "DateKey", "Period", "DistanceKM"]]
    
    logger.info("STAGE 4: %d rijen vóór dedup tegen DB", len(final_fact))

    final_fact = filterNewRows(final_fact, "FactStaffCommute", ["StaffKey", "DateKey"])
    logger.info("STAGE 5: %d echt nieuwe rijen — wordt naar DB geschreven", len(final_fact))
    return final_fact


if __name__ == "__main__":
    print(fillDimStaff().head(10))
    print(fillFactStaffCommute().head(10))