import logging
import requests
import re
import json
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from DWH.connection.connect import getData

logger = logging.getLogger(__name__)


# Scraping helpers 

def data_ophalen(url, counting_point_id, headers):
    """Haal teldata op van één URL en geef een lijst van records terug."""
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        html = r.text
        records = []

        # 2 richtingen
        start_match = re.search(r'directionGraphData\\?":\s*(\[)', html)
        if start_match:
            start_index = start_match.start(1)
            bracket_count = 0
            for i in range(start_index, len(html)):
                if html[i] == '[': bracket_count += 1
                elif html[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_index = i + 1
                        break
            direction_data = json.loads(
                html[start_index:end_index].replace('\\"', '"').encode('utf-8').decode('unicode_escape')
            )
            d_in  = next((d for d in direction_data if d.get('direction') == 'in'),  None)
            d_out = next((d for d in direction_data if d.get('direction') == 'out'), None)
            if d_in and d_out:
                for entry_in, entry_out in zip(d_in['data'], d_out['data']):
                    dt = entry_in['timestamp'].split("T")[0]
                    c_in  = entry_in['traffic']['counts']
                    c_out = entry_out['traffic']['counts']
                    records.append({
                        "CountingPointID":    counting_point_id,
                        "Date":               dt,
                        "DirectionInCounts":  c_in,
                        "DirectionOutCounts": c_out,
                        "TotalCounts":        c_in + c_out,
                    })
        else:
            # 1 richting
            start_match = re.search(r'chartData\\?":\s*(\[)', html)
            if start_match:
                start_index = start_match.start(1)
                bracket_count = 0
                for i in range(start_index, len(html)):
                    if html[i] == '[': bracket_count += 1
                    elif html[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_index = i + 1
                            break
                chart_data = json.loads(
                    html[start_index:end_index].replace('\\"', '"').encode('utf-8').decode('unicode_escape')
                )
                for sensor in chart_data:
                    for d in sensor.get('data', []):
                        dt    = d['timestamp'].split("T")[0]
                        count = d['traffic']['counts']
                        records.append({
                            "CountingPointID":    counting_point_id,
                            "Date":               dt,
                            "DirectionInCounts":  count,
                            "DirectionOutCounts": 0,
                            "TotalCounts":        count,
                        })
        return records
    except Exception:
        return []


def haal_direction_data_per_paal(counting_point_id, firstData, jaren_in_db=set(), maanden_in_db=set()):
    """
    Haal alle teldata op voor één telpaal.
    Slaat jaren/maanden over die al in de DB zitten.
    """
    records = []
    headers = {"User-Agent": "Mozilla/5.0"}

    start_year   = int(firstData.split('-')[0])
    huidig_jaar  = datetime.today().year
    huidige_maand = datetime.today().month

    for year in range(start_year, huidig_jaar + 1):
        if year < huidig_jaar and year in jaren_in_db:
            continue
        if year < huidig_jaar:
            url = f"https://fietsflow.eco-counter.com/site/{counting_point_id}?year={year}"
            records.extend(data_ophalen(url, counting_point_id, headers))
        else:
            for month in range(1, huidige_maand + 1):
                if month < huidige_maand and (year, month) in maanden_in_db:
                    continue
                if month == huidige_maand:
                    url = f"https://fietsflow.eco-counter.com/site/{counting_point_id}"
                else:
                    url = f"https://fietsflow.eco-counter.com/site/{counting_point_id}?year={year}&month={month}"
                records.extend(data_ophalen(url, counting_point_id, headers))
                time.sleep(0.1)

    if records:
        df = pd.DataFrame(records)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    return pd.DataFrame()


def _scrape_paal(row, jaren_in_db, maanden_in_db):
    """Worker-functie voor ThreadPoolExecutor: scrape één telpaal."""
    pid = int(row["CountingPointID"])
    try:
        df = haal_direction_data_per_paal(
            pid,
            str(row["FirstData"]),
            jaren_in_db=jaren_in_db.get(pid, set()),
            maanden_in_db=maanden_in_db.get(pid, set()),
        )
        return pid, df
    except Exception as e:
        logger.exception("Fout bij paal %d", pid)
        return pid, pd.DataFrame()


# Hoofdfunctie 

def haal_all_counts(df_telpalen, engine=None, max_workers=10):
    """
    Scrapt teldata voor alle telpalen in parallel (ThreadPoolExecutor).

    - max_workers: aantal gelijktijdige HTTP-verbindingen (standaard 10).
      Verhoog naar 15-20 als de server het toelaat; verlaag bij time-outs.
    - Yieldt per telpaal een DataFrame zodat de aanroeper direct naar de DB
      kan schrijven zonder alles in RAM te houden.
    - Als engine meegegeven wordt, worden al bekende jaren/maanden per paal
      opgehaald zodat enkel nieuwe data wordt gescrapt.
    """
    jaren_per_paal   = {}
    maanden_per_paal = {}
    huidig_jaar      = datetime.today().year

    # Bestaande data in DB ophalen voor incrementeel laden
    if engine is not None:
        pids   = ", ".join(str(int(p)) for p in df_telpalen["CountingPointID"])
        result = getData(engine, query=f"""
            SELECT DISTINCT CountingPointID,
                LEFT(CAST(DateKey AS VARCHAR), 4)      AS Jaar,
                SUBSTRING(CAST(DateKey AS VARCHAR), 5, 2) AS Maand
            FROM FactCountings
            WHERE CountingPointID IN ({pids})
        """)
        if result is not None and not result.empty:
            for pid, groep in result.groupby("CountingPointID"):
                pid   = int(pid)
                jaren = groep[groep["Jaar"].astype(int) < huidig_jaar]["Jaar"].astype(int)
                jaren_per_paal[pid] = set(jaren.tolist())

                maanden = groep[groep["Jaar"].astype(int) == huidig_jaar]
                maanden_per_paal[pid] = set(
                    zip(maanden["Jaar"].astype(int), maanden["Maand"].astype(int))
                )

    rijen  = [row for _, row in df_telpalen.iterrows()]
    totaal = len(rijen)
    klaar  = 0

    # Parallel scrapen: HTTP-calls zijn I/O-bound → threading helpt sterk
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_scrape_paal, row, jaren_per_paal, maanden_per_paal): row
            for row in rijen
        }

        for future in as_completed(futures):
            pid, df = future.result()
            klaar += 1
            if klaar % 20 == 0 or klaar == totaal:
                logger.info("%d/%d telpalen verwerkt...", klaar, totaal)
            if df is not None and not df.empty:
                yield df