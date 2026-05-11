import pandas as pd
from pathlib import Path
import sys

from data_gathering.hulp_functies import filterNewRows

# Zorg dat de root wordt gevonden, pas dit pad aan indien nodig
ROOT = Path(__file__).resolve().parents[2] # parents[2] gaat twee mappen omhoog vanaf hier
sys.path.append(str(ROOT))


def fillTransportType():
    df = pd.read_csv(ROOT / "data" / "uitstoot_in_kg_CO2_per_km", sep=";")

    df.columns = ["VehicleType", "CO2PerKM"]

    df = filterNewRows(df, 'DimTransportType', 'VehicleType')
    
    return df