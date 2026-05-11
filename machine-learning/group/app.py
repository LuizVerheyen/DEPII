import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from difflib import get_close_matches

import joblib
import numpy as np
import pandas as pd
import speech_recognition as sr
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ─── project root ─────────────────────────────────────────────────────────────
ROOT = Path.cwd()
while ROOT != ROOT.parent and not (ROOT / 'DWH').exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from DWH.connection.connect import get_engine, getData

load_dotenv()

# ─── model directories ────────────────────────────────────────────────────────
MODELS_WEER     = ROOT / 'machine-learning' / 'models' / 'weer' / 'v2'
MODELS_FIETSERS = ROOT / 'machine-learning' / 'models' / 'fietsers'
MODELS_BLUEBIKE = ROOT / 'machine-learning' / 'models' / 'bluebike'


def safe_filename(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip())


# ─── data ophalen (gecached) ──────────────────────────────────────────────────

@st.cache_resource
def get_alle_stations(_engine) -> list[str]:
    df = getData(_engine, "SELECT Name FROM DimWeatherStation ORDER BY Name;")
    return df['Name'].tolist()


@st.cache_resource
def get_alle_telpalen(_engine) -> list[str]:
    df = getData(_engine, "SELECT CountingPointName FROM DimCountingPoint ORDER BY CountingPointName;")
    return df['CountingPointName'].tolist()


@st.cache_resource
def get_alle_bluebike_stations(_engine) -> list[str]:
    df = getData(_engine, "SELECT LocationName FROM DimBlueBikeStation ORDER BY LocationName;")
    return df['LocationName'].tolist()


# ─── model laden ──────────────────────────────────────────────────────────────

def load_model(pad: Path, label: str):
    if not pad.exists():
        raise FileNotFoundError(
            f"Geen model gevonden voor '{label}'.\n"
            f"Verwacht: {pad}\n"
            f"Voer eerst train_models.py uit."
        )
    return joblib.load(pad)


def load_weer_model(station: str):
    pad = MODELS_WEER / f"model_gem_temp_{safe_filename(station)}.pkl"
    return load_model(pad, station)


def load_fietsers_model(telpaal: str):
    pad = MODELS_FIETSERS / f"model_fietsers_{safe_filename(telpaal)}.pkl"
    return load_model(pad, telpaal)


def load_bluebike_model(station: str):
    pad = MODELS_BLUEBIKE / f"model_bluebike_{safe_filename(station)}.pkl"
    return load_model(pad, station)


# ─── LLM ──────────────────────────────────────────────────────────────────────

@st.cache_resource
def match_locatie(input_locatie, lijst):
    input_locatie = input_locatie.lower().strip()
    
    lijst_lower = {x.lower(): x for x in lijst}
    match = get_close_matches(input_locatie, lijst_lower.keys(), n=1, cutoff=0.6)

    return lijst_lower[match[0]] if match else "onbekend"

def get_llm():
    return ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("groq_API"),
    )


def bepaal_intentie(transcript: str,
                    weer_stations: list[str],
                    telpalen: list[str],
                    bluebike_stations: list[str]) -> dict:

    # weer_str     = "\n".join(f"  - {s}" for s in weer_stations)
    # fiets_str    = "\n".join(f"  - {s}" for s in telpalen)
    # bluebike_str = "\n".join(f"  - {s}" for s in bluebike_stations)

    prompt = f"""
Je bent een assistent die gesproken vragen analyseert over voorspellingen.

Gesproken vraag:
----------------------
{transcript}
----------------------

Lijst van weerstations:
-------------------------
{weer_stations}
-------------------------



Extraheer de volgende informatie:
1. onderwerp: kies uit [weer, fietsers, blue-bikes, onbekend]
2. locatie: als het onderwerp weer is -> pak het dichtsbijzijnde weerstation model van de locatie zoals uitgesproken door de gebruiker kies uit de lijst weer stations die ik je heb gegeven. anders als het onderwerp niet weer is hou je de locatie zoals gezegt. BEHOUD volledige naam (bv. "Deinze Parking Leiespiegel", "Leuven Station Tiensevest"). GEEN inkorting naar enkel stadnaam. (of "onbekend")
3. dagen: het aantal dagen vooruit (tussen 1 en 7, standaard 1)

ANTWOORD ENKEL met geldige JSON, geen uitleg, geen extra tekst:
{{"onderwerp": "...", "locatie": "...", "dagen": ...}}
"""
    antwoord = get_llm().invoke(prompt).content.strip()
    return json.loads(antwoord)


# ─── spraakherkenning ─────────────────────────────────────────────────────────

def luister_naar_vraag() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Luisteren… spreek nu.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source, phrase_time_limit=10)
    return recognizer.recognize_google(audio, language="nl-NL").lower()


# ─── voorspellingen ───────────────────────────────────────────────────────────

def toekomstige_datums(dagen: int) -> pd.DataFrame:
    today = datetime.today()
    dates = [today + timedelta(days=i) for i in range(1, dagen + 1)]
    df = pd.DataFrame({"Date": dates})
    df["Month"]     = df["Date"].dt.month
    df["DayOfYear"] = df["Date"].dt.dayofyear
    df["DayOfWeek"] = df["Date"].dt.dayofweek
    df["Datum"]     = df["Date"].dt.strftime("%A %d %b %Y")
    return df


def maak_weer_voorspelling(station: str, dagen: int) -> pd.DataFrame:
    model = load_weer_model(station)
    df = toekomstige_datums(dagen)
    df["Voorspelling (°C)"] = model.predict(df[["Month", "DayOfYear"]])
    return df[["Datum", "Voorspelling (°C)"]]


def maak_fietsers_voorspelling(telpaal: str, dagen: int) -> pd.DataFrame:
    model  = load_fietsers_model(telpaal)
    engine = get_engine()
    today  = datetime.today().date()

    # Haal de laatste 30 werkelijke tellingen op als startbasis voor de lag-features
    recent = getData(engine, f"""
        SELECT TOP 30 d.FullDateAlternateKey AS Date, fc.TotalCounts
        FROM FactCountings fc
        JOIN DimCountingPoint cp ON fc.CountingPointID = cp.CountingPointID
        JOIN DimDate d ON fc.DateKey = d.DateKey
        WHERE cp.CountingPointName = '{telpaal}'
        ORDER BY d.FullDateAlternateKey DESC;
    """)
    if recent is None or recent.empty:
        history = [100.0] * 30
    else:
        recent["Date"] = pd.to_datetime(recent["Date"])
        history = recent.sort_values("Date")["TotalCounts"].astype(float).tolist()

    # IsHoliday voor de toekomstige datums ophalen uit DimDate
    toekomst = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, dagen + 1)]
    dates_sql = "', '".join(toekomst)
    hol_df = getData(engine, f"""
        SELECT FullDateAlternateKey AS Date, IsHoliday
        FROM DimDate
        WHERE FullDateAlternateKey IN ('{dates_sql}');
    """)
    holiday_map = {}
    if hol_df is not None and not hol_df.empty:
        hol_df["Date"] = pd.to_datetime(hol_df["Date"])
        holiday_map = dict(zip(hol_df["Date"], hol_df["IsHoliday"].astype(int)))

    # Toekomstige datums met kalenderfeatures
    df = toekomstige_datums(dagen)

    # Recursieve voorspelling: elke dag gebruikt de voorspelling van de vorige dag als lag
    predictions = []
    for _, row in df.iterrows():
        lag1         = history[-1]
        lag7         = history[-7] if len(history) >= 7 else history[0]
        rolling_mean = float(np.mean(history[-7:])) if len(history) >= 7 else float(np.mean(history))
        is_weekend   = int(row["DayOfWeek"] >= 5)
        is_holiday   = holiday_map.get(pd.Timestamp(row["Date"]), 0)

        feat = pd.DataFrame([{
            "Lag1":         lag1,
            "Lag7":         lag7,
            "RollingMean7": rolling_mean,
            "DayOfWeek":    row["DayOfWeek"],
            "Month":        row["Month"],
            "IsWeekend":    is_weekend,
            "IsHoliday":    is_holiday,
        }])
        pred = float(max(model.predict(feat)[0], 0))
        predictions.append(round(pred))
        history.append(pred)

    df["Voorspelling (fietsers)"] = predictions
    return df[["Datum", "Voorspelling (fietsers)"]]


def maak_bluebike_voorspelling(station: str, dagen: int) -> pd.DataFrame:
    try:
        model = load_bluebike_model(station)
    except FileNotFoundError:
        raise ValueError(f"Geen model gevonden voor Blue-bike station '{station}'. "
                        f"Train eerst het model met train_bluebike.py")
    engine = get_engine()

    # laatste waarden ophalen (voor Lag7)
    recent = getData(engine, f"""
        WITH UitleenData AS (
            SELECT 
                f.BlueBikeStationKey,
                f.DateKey,
                f.TimeKey,
                f.BikesInUse,
                LAG(f.BikesInUse) OVER (
                    PARTITION BY f.BlueBikeStationKey, f.DateKey 
                    ORDER BY f.TimeKey
                ) AS PrevBikesInUse
            FROM FactBlueBike f
        ),
        UitleningenPerDag AS (
            SELECT
                BlueBikeStationKey,
                DateKey,
                CASE 
                    WHEN PrevBikesInUse IS NOT NULL AND BikesInUse > PrevBikesInUse 
                    THEN BikesInUse - PrevBikesInUse
                    ELSE 0
                END AS Uitleningen
            FROM UitleenData
        )
        SELECT TOP 30
            s.LocationName,
            d.FullDateAlternateKey AS Date,
            SUM(u.Uitleningen) AS UitleningenPerDag
        FROM UitleningenPerDag u
        JOIN DimBlueBikeStation s ON s.BlueBikeStationKey = u.BlueBikeStationKey
        JOIN DimDate d ON d.DateKey = u.DateKey
        WHERE s.LocationName = '{station}'
        GROUP BY s.LocationName, d.FullDateAlternateKey
        ORDER BY d.FullDateAlternateKey DESC;
    """)

    if recent is None or recent.empty:
        st.warning(f"⚠️ Geen historische data voor '{station}'. Gebruik fallback waarden.")
        history = [1.0] * 30
    else:
        recent["Date"] = pd.to_datetime(recent["Date"])
        history = recent.sort_values("Date")["UitleningenPerDag"].astype(float).tolist()

    df = toekomstige_datums(dagen)

    predictions = []

    for _, row in df.iterrows():
        lag7 = history[-7] if len(history) >= 7 else history[0]

        feat = pd.DataFrame([{
            "DayOfWeek": row["DayOfWeek"],
            "Month": row["Month"],
            "Lag7": lag7
        }])

        pred = max(model.predict(feat)[0], 0)
        predictions.append(round(pred, 1))

        history.append(pred)

    df["Voorspelling (uitgeleende fietsen)"] = predictions
    return df[["Datum", "Voorspelling (uitgeleende fietsen)"]]


# ─── dashboard tonen ──────────────────────────────────────────────────────────

def toon_resultaat(onderwerp: str, locatie_key: str, dagen: int):
    if onderwerp == "weer":
        with st.spinner(f"🔮 Weersvoorspelling voor {locatie_key}…"):
            df_result = maak_weer_voorspelling(locatie_key, dagen)
        st.subheader(f"🌡️ Weersvoorspelling – {locatie_key}")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
        df_plot = df_result.copy()
        df_plot.index = range(1, len(df_plot) + 1)
        st.line_chart(df_plot["Voorspelling (°C)"])

    elif onderwerp == "fietsers":
        with st.spinner(f"🔮 Fietsersvoorspelling voor {locatie_key}…"):
            df_result = maak_fietsers_voorspelling(locatie_key, dagen)
        st.subheader(f"🚲 Fietsersvoorspelling – {locatie_key}")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
        df_plot = df_result.copy()
        df_plot.index = range(1, len(df_plot) + 1)
        st.bar_chart(df_plot["Voorspelling (fietsers)"])

    elif onderwerp == "blue-bikes":
        with st.spinner(f"🔮 Blue-bike voorspelling voor {locatie_key}…"):
            df_result = maak_bluebike_voorspelling(locatie_key, dagen)
        st.subheader(f"🔵 Blue-bike voorspelling – {locatie_key}")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
        df_plot = df_result.copy()
        df_plot.index = range(1, len(df_plot) + 1)
        st.bar_chart(df_plot["Voorspelling (uitgeleende fietsen)"])

    else:
        st.warning("❓ Onderwerp niet herkend. Probeer een vraag over **weer**, **fietsers** of **blue-bikes**.")


# ─── Streamlit UI ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Voorspellingen Dashboard", page_icon="🌤️", layout="centered")
    st.title("🌤️ Voorspellingen Dashboard")
    st.caption("Stel mondeling een vraag over weer, fietsers of blue-bikes — 1 tot 7 dagen vooruit.")

    engine = get_engine()
    weer_stations     = get_alle_stations(engine)
    telpalen          = get_alle_telpalen(engine)
    bluebike_stations = get_alle_bluebike_stations(engine)

    # Sessie-state
    for key in ["transcript", "fout"]:
        if key not in st.session_state:
            st.session_state[key] = ""
    for key in ["intent", "resultaat"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # ── Input ──
    col1, col2 = st.columns([1, 3])
    with col1:
        spreek = st.button("🎤 Spreek vraag in", use_container_width=True)
    with col2:
        handmatig = st.text_input(
            "…of typ je vraag:",
            placeholder="Geef de weersvoorspelling voor morgen in Gent"
        )

    vraag_tekst = ""
    if spreek:
        try:
            vraag_tekst = luister_naar_vraag()
            st.session_state.transcript = vraag_tekst
        except sr.UnknownValueError:
            st.error("❌ Kon de spraak niet verstaan. Probeer opnieuw.")
        except sr.RequestError as e:
            st.error(f"❌ Spraakherkenningsfout: {e}")
    elif handmatig:
        vraag_tekst = handmatig.lower()
        st.session_state.transcript = vraag_tekst

    # ── Verwerking ──
    if vraag_tekst:
        with st.spinner("🤔 Intentie bepalen…"):
            try:
                intent = bepaal_intentie(
                    vraag_tekst,
                    weer_stations,
                    telpalen,
                    bluebike_stations
                )
                st.session_state.intent = intent
            except json.JSONDecodeError:
                st.error("❌ Kon de intentie niet bepalen. Probeer een duidelijkere vraag.")
                st.stop()

        intent      = st.session_state.intent
        locatie     = intent.get("locatie", "onbekend")
        onderwerp   = intent.get("onderwerp", "onbekend")
        dagen       = max(1, min(7, int(intent.get("dagen", 1))))

        if onderwerp == "weer":
            locatie_key = match_locatie(locatie, weer_stations)

        elif onderwerp == "fietsers":
            locatie_key = match_locatie(locatie, telpalen)

        elif onderwerp == "blue-bikes":
            locatie_key = match_locatie(locatie, bluebike_stations)

        else:
            locatie_key = "onbekend"

        # Transcript & metrics
        st.success(f"📝 Transcript: *{st.session_state.transcript}*")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("📍 Locatie", locatie.title())
        col_b.metric("🏷️ Onderwerp", onderwerp)
        col_c.metric("📅 Dagen", dagen)
        
        # Voorspelling tonen
        try:
            toon_resultaat(onderwerp, locatie_key, dagen)
        except FileNotFoundError as e:
            st.error(str(e))


if __name__ == "__main__":
    main()
