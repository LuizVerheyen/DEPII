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

FEATURES = ["DayOfWeek", "Month", "Lag7"]
TARGET   = "UitleningenPerDag"


def safe_filename(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip())


def train_alle_stations(engine, model_dir: Path):
    model_dir.mkdir(parents=True, exist_ok=True)

    stations = getData(engine, """
        SELECT BlueBikeStationKey, LocationName
        FROM DimBlueBikeStation
        ORDER BY LocationName;
    """)

    print(f"\n Blue-bike: {len(stations)} stations\n")

    for _, row in stations.iterrows():
        sk   = row["BlueBikeStationKey"]
        naam = row["LocationName"]

        # Zelfde query als jouw analyse
        df = getData(engine, f"""
            WITH UitleenData AS (
                SELECT 
                    f.BlueBikeStationKey,
                    f.DateKey,
                    f.BikesInUse,
                    LAG(f.BikesInUse) OVER (
                        PARTITION BY f.BlueBikeStationKey, f.DateKey 
                        ORDER BY f.TimeKey
                    ) AS PrevBikesInUse
                FROM FactBlueBike f
            )
            SELECT
                d.FullDateAlternateKey AS Date,
                SUM(CASE 
                    WHEN PrevBikesInUse IS NOT NULL AND BikesInUse > PrevBikesInUse 
                    THEN BikesInUse - PrevBikesInUse
                    ELSE 0
                END) AS UitleningenPerDag
            FROM UitleenData u
            JOIN DimDate d ON u.DateKey = d.DateKey
            WHERE u.BlueBikeStationKey = {sk}
            GROUP BY d.FullDateAlternateKey
            ORDER BY d.FullDateAlternateKey;
        """)

        if df is None or df.empty:
            print(f"[SKIP] {naam}: geen data")
            continue

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        # features
        df["DayOfWeek"] = df["Date"].dt.dayofweek
        df["Month"]     = df["Date"].dt.month
        df["Lag7"]      = df["UitleningenPerDag"].shift(7)

        df = df.dropna()

        if len(df) < 30:
            print(f"[SKIP] {naam}: te weinig data")
            continue

        # split
        split = int(len(df) * 0.8)
        train = df.iloc[:split]
        test  = df.iloc[split:]

        model = LinearRegression()
        model.fit(train[FEATURES], train[TARGET])

        preds = model.predict(test[FEATURES])
        mae = mean_absolute_error(test[TARGET], preds)

        pad = model_dir / f"model_bluebike_{safe_filename(naam)}.pkl"
        joblib.dump(model, pad)

        print(f"[OK] {naam:40s} MAE={mae:.2f}")

def main():
    engine = get_engine()
    model_dir = ROOT / 'machine-learning' / 'models' / 'bluebike'

    train_alle_stations(engine, model_dir)


if __name__ == "__main__":
    main()