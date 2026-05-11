"""
Train RandomForestRegressor voor alle fietstelpalen en exporteer naar models/fietsers/.

Features zijn identiek aan de analyse in arne.ipynb:
  Lag1, Lag7, RollingMean7, DayOfWeek, Month, IsWeekend, IsHoliday

Uitvoeren vanuit de machine-learning/ map:
    python train_fietsers.py
"""
import re
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

ROOT = Path.cwd()
while ROOT != ROOT.parent and not (ROOT / 'DWH').exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from DWH.connection.connect import get_engine, getData

FEATURES = ['Lag1', 'Lag7', 'RollingMean7', 'DayOfWeek', 'Month', 'IsWeekend', 'IsHoliday']
TARGET   = 'TotalCounts'


def safe_filename(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip())


def train_alle_telpalen(engine, model_dir: Path) -> list[dict]:
    model_dir.mkdir(parents=True, exist_ok=True)

    telpalen = getData(
        engine,
        "SELECT CountingPointID, CountingPointName "
        "FROM DimCountingPoint ORDER BY CountingPointName;"
    )
    print(f"\n  Fietsers (RandomForest): {len(telpalen)} telpalen\n")

    resultaten = []

    for _, row in telpalen.iterrows():
        cp_id   = int(row['CountingPointID'])
        cp_naam = row['CountingPointName']

        df = getData(engine, f"""
            SELECT d.FullDateAlternateKey AS Date,
                   d.IsHoliday,
                   f.TotalCounts
            FROM FactCountings f
            JOIN DimDate d ON f.DateKey = d.DateKey
            WHERE f.CountingPointID = {cp_id}
            ORDER BY d.FullDateAlternateKey;
        """)

        if df is None or df.empty:
            print(f"  [SKIP] {cp_naam}: geen data")
            continue

        df['Date']         = pd.to_datetime(df['Date'])
        df['Month']        = df['Date'].dt.month
        df['DayOfWeek']    = df['Date'].dt.dayofweek          # 0=ma … 6=zo
        df['IsWeekend']    = (df['DayOfWeek'] >= 5).astype(int)
        df['IsHoliday']    = df['IsHoliday'].astype(int)
        df['Lag1']         = df[TARGET].shift(1)
        df['Lag7']         = df[TARGET].shift(7)
        df['RollingMean7'] = df[TARGET].shift(1).rolling(7, min_periods=3).mean()

        df = df.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)

        if len(df) < 30:
            print(f"  [SKIP] {cp_naam}: te weinig data na feature engineering ({len(df)} rijen)")
            continue

        # Chronologische split: eerste 80% training, laatste 20% test
        split    = int(len(df) * 0.8)
        train_df = df.iloc[:split]
        test_df  = df.iloc[split:].copy()

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(train_df[FEATURES], train_df[TARGET])

        mae = mean_absolute_error(test_df[TARGET], model.predict(test_df[FEATURES]))
        
        gem_counts = df[TARGET].mean()
        
        mape = (mae / gem_counts * 100) if gem_counts > 0 else None

        resultaten.append({
            "label": cp_naam,
            "mae": mae,
            "mean_counts": round(gem_counts, 1),
            "mape": round(mape, 1) if mape else None
        })

        pad = model_dir / f"model_fietsers_{safe_filename(cp_naam)}.pkl"
        joblib.dump(model, pad)
        print(f"  [OK]   {cp_naam:<50s}  MAE={mae:6.1f}  → {pad.name}")
        resultaten.append({"label": cp_naam, "mae": mae})

    return resultaten


def main():
    engine    = get_engine()
    model_dir = ROOT / 'machine-learning' / 'models' / 'fietsers'

    resultaten = train_alle_telpalen(engine, model_dir)

    if not resultaten:
        print("\n Geen modellen getraind.")
        return

    df_eval = pd.DataFrame(resultaten).sort_values('mae')
    df_eval.to_csv(model_dir / 'evaluatie_rf.csv', index=False)

    print(f"\n{'='*60}")
    print(f"  {len(resultaten)} modellen getraind en opgeslagen in {model_dir}")
    print(f"    Gem. MAE : {df_eval['mae'].mean():.1f} fietsers/dag")
    print(f"    Beste    : {df_eval.iloc[0]['label']}  (MAE={df_eval.iloc[0]['mae']:.1f})")
    print(f"    Slechtste: {df_eval.iloc[-1]['label']}  (MAE={df_eval.iloc[-1]['mae']:.1f})")
    print(f"{'='*60}")
    
    print(f"    Gem. MAPE: {df_eval['mape'].mean():.1f}%")


if __name__ == "__main__":
    main()
