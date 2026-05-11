import re
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

ROOT = Path.cwd()
while ROOT != ROOT.parent and not (ROOT / 'DWH').exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from DWH.connection.connect import get_engine, getData


# helpers -> hulp met AI

def safe_filename(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip())


def train_en_sla_op(df: pd.DataFrame, target_col: str, features: list[str],
                    model_path: Path, label: str) -> dict | None:
    """Generieke train/evalueer/sla-op functie."""
    df = df.dropna(subset=features + [target_col])
    if len(df) < 30:
        print(f"  [SKIP] {label}: te weinig data ({len(df)} rijen)")
        return None

    split = int(len(df) * 0.8)
    train = df.iloc[:split]
    test  = df.iloc[split:].copy()

    model = LinearRegression()
    model.fit(train[features], train[target_col])

    test["Prediction"] = model.predict(test[features])
    mae = mean_absolute_error(test[target_col], test["Prediction"])

    joblib.dump(model, model_path)
    print(f"  [OK]   {label:45s}  MAE={mae:.2f}  → {model_path.name}")
    return {"label": label, "mae": mae}


# weather 

def train_weer(engine, model_dir: Path) -> list[dict]:
    model_dir.mkdir(parents=True, exist_ok=True)
    stations = getData(engine, "SELECT Name FROM DimWeatherStation ORDER BY Name;")['Name'].tolist()
    print(f"\n🌤️  Weer: {len(stations)} stations")
    resultaten = []
    for naam in stations:
        query = f"""
            SELECT d.FullDateAlternateKey AS Date, d.Month, d.DayOfYear, m.TempAvg
            FROM FactMeteo m
            JOIN DimDate d            ON m.DateKey           = d.DateKey
            JOIN DimWeatherStation ws ON m.WeatherStationKey = ws.WeatherstationID
            WHERE ws.Name = '{naam}'
            ORDER BY d.FullDateAlternateKey;
        """
        df = getData(engine, query)
        df['Date']      = pd.to_datetime(df['Date'])
        df['Month']     = df['Date'].dt.month
        df['DayOfYear'] = df['Date'].dt.dayofyear

        pad = model_dir / f"model_gem_temp_{safe_filename(naam)}.pkl"
        r = train_en_sla_op(df, "TempAvg", ["Month", "DayOfYear"], pad, naam)
        if r:
            resultaten.append(r)
    return resultaten


# bikertjes

def train_fietsers(engine, model_dir: Path) -> list[dict]:
    model_dir.mkdir(parents=True, exist_ok=True)
    telpalen = getData(engine, "SELECT CountingPointID, CountingPointName FROM DimCountingPoint ORDER BY CountingPointName;")
    print(f"\n🚲  Fietsers: {len(telpalen)} telpalen")
    resultaten = []
    for _, row in telpalen.iterrows():
        cp_id  = row['CountingPointID']
        cp_naam = row['CountingPointName']
        query = f"""
            SELECT d.FullDateAlternateKey AS Date, d.Month, d.DayOfYear, d.DayOfWeek,
                   f.TotalCounts
            FROM FactCountings f
            JOIN DimDate d ON f.DateKey = d.DateKey
            WHERE f.CountingPointID = {cp_id}
            ORDER BY d.FullDateAlternateKey;
        """
        df = getData(engine, query)
        df['Date']      = pd.to_datetime(df['Date'])
        df['Month']     = df['Date'].dt.month
        df['DayOfYear'] = df['Date'].dt.dayofyear
        df['DayOfWeek'] = df['Date'].dt.dayofweek  # 0=ma … 6=zo

        pad = model_dir / f"model_fietsers_{safe_filename(cp_naam)}.pkl"
        r = train_en_sla_op(df, "TotalCounts", ["Month", "DayOfYear", "DayOfWeek"], pad, cp_naam)
        if r:
            resultaten.append(r)
    return resultaten


# bluebikes

def train_bluebike(engine, model_dir: Path) -> list[dict]:
    model_dir.mkdir(parents=True, exist_ok=True)
    # Haal unieke stations op
    stations = getData(engine, """
        SELECT DISTINCT s.BlueBikeStationKey, s.LocationName
        FROM DimBlueBikeStation s
        ORDER BY s.LocationName;
    """)
    print(f"\n🔵  Blue-bikes: {len(stations)} stations")
    resultaten = []
    for _, row in stations.iterrows():
        sk    = row['BlueBikeStationKey']
        naam  = row['LocationName']
        # per dag: gemiddeld aantal uitgeleende fietsen
        query = f"""
            SELECT d.FullDateAlternateKey AS Date, d.Month, d.DayOfYear, d.DayOfWeek,
                   AVG(CAST(f.BikesInUse AS FLOAT)) AS AvgBikesInUse
            FROM FactBlueBike f
            JOIN DimDate d ON f.DateKey = d.DateKey
            WHERE f.BlueBikeStationKey = {sk}
              AND f.BikesInUse IS NOT NULL
            GROUP BY d.FullDateAlternateKey, d.Month, d.DayOfYear, d.DayOfWeek
            ORDER BY d.FullDateAlternateKey;
        """
        df = getData(engine, query)
        df['Date']      = pd.to_datetime(df['Date'])
        df['Month']     = df['Date'].dt.month
        df['DayOfYear'] = df['Date'].dt.dayofyear
        df['DayOfWeek'] = df['Date'].dt.dayofweek

        pad = model_dir / f"model_bluebike_{safe_filename(naam)}.pkl"
        r = train_en_sla_op(df, "AvgBikesInUse", ["Month", "DayOfYear", "DayOfWeek"], pad, naam)
        if r:
            resultaten.append(r)
    return resultaten


# main functieeee

def main():
    engine = get_engine()

    res_weer     = train_weer    (engine, Path("./models/weer"))
    res_fietsers = train_fietsers(engine, Path("./models/fietsers"))
    res_bluebike = train_bluebike(engine, Path("./models/bluebike"))

    totaal = len(res_weer) + len(res_fietsers) + len(res_bluebike)
    print(f"\n✅ {totaal} modellen getraind")
    print(f"   Weer:       {len(res_weer)}")
    print(f"   Fietsers:   {len(res_fietsers)}")
    print(f"   Blue-bikes: {len(res_bluebike)}")

    # overzicht opslaan
    alle = (
        [{"type": "weer",      **r} for r in res_weer]
      + [{"type": "fietsers",  **r} for r in res_fietsers]
      + [{"type": "blue-bike", **r} for r in res_bluebike]
    )
    pd.DataFrame(alle).to_csv("./models/evaluatie.csv", index=False)
    print("📄 Evaluatie: models/evaluatie.csv")


if __name__ == "__main__":
    main()
