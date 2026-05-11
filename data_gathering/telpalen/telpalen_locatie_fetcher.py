import logging
import time

import requests
import re
import pandas as pd
import codecs
import json

logger = logging.getLogger(__name__)

def empty_to_none(value):
    if value is None or str(value).strip() == "":
        return None
    return value

def quick_find(pattern, text, group=1):
    m = re.search(pattern, text)
    return m.group(group).strip() if m else ""

def clean_text(text):
    if not text: return ""
    try:
        text = codecs.decode(text, 'unicode_escape')
        text = text.encode('latin-1').decode('utf-8')
    except:
        pass 
    text = re.sub(r'<.*?>', '', text)
    return text.strip(',').strip()

def geocodeer(straat, nummer, postcode, gemeente):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "street": f"{nummer} {straat}",
        "postalcode": postcode,
        "city": gemeente,
        "country": "Belgium",
        "format": "json",
        "limit": 1
    }
    try:
        time.sleep(1.6)
        r = requests.get(url, params=params, headers={"User-Agent": "dep2526g09@gmail.com"}, timeout=10)
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        logger.warning("Geocoding fout: %s", e)
    return None, None

def haal_richtingsnamen(counting_point_id):
    url = f"https://fietsflow.eco-counter.com/site/{counting_point_id}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        html = r.text
        
        # Zoek directionGraphData
        match = re.search(r'directionGraphData\\?":\s*(\[)', html)
        if match:
            start = match.start(1)
            depth, end = 0, 0
            for i in range(start, len(html)):
                if html[i] == '[': depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            cleaned = html[start:end].replace('\\"', '"').encode('utf-8').decode('unicode_escape')
            direction_data = json.loads(cleaned)
            
            d_in = next((d for d in direction_data if d.get('direction') == 'in'), None)
            d_out = next((d for d in direction_data if d.get('direction') == 'out'), None)
            
            name_in = d_in['directionName'].split('->')[0].strip() if d_in else None
            name_out = d_out['directionName'].split('->')[0].strip() if d_out else None
            return name_in, name_out
        
        # Geen richting → unidirectioneel, gebruik sitenaam als label
        title_match = re.search(r'<title>(.*?)</title>', html)
        naam = title_match.group(1).strip() if title_match else None
        return naam, None
        
    except Exception as e:
        logger.exception("Fout bij ophalen richtingsnamen voor telpaal %s", counting_point_id)
        return None, None

# Als engine meegegeven wordt, worden telpalen die al in DimCountingPoint staan automatisch overgeslagen
def haal_telpalen_volledig_op(existing_ids=None):
    if existing_ids is None:
        existing_ids = set()

    existing_ids = set(map(int, existing_ids)) if existing_ids else set()

    url = "https://fietsflow.eco-counter.com"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        r.encoding = 'utf-8'
        html = r.text
    except Exception as e:
        logger.exception("Fout bij verbinding met fietsflow.eco-counter.com")
        return None

    # Next.js data extractie
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
    big_text = "".join(chunks).replace('\\"', '"').replace("\\\\", "\\")
    raw_objects = re.split(r'(?=\{"id":\d{8,},)', big_text)
    
    resultaten = []
    seen_ids = set()
    skipped = 0

    for chunk in raw_objects:
        pid = quick_find(r'^\{"id":(\d+)', chunk)
        
        if not pid or pid in seen_ids or '"location":{' not in chunk:
            continue

        if int(pid) in existing_ids:
            seen_ids.add(pid)
            skipped += 1
            continue
            
        name = clean_text(quick_find(r'"name":"(.*?)"', chunk))
        description = clean_text(quick_find(r'"description":"(.*?)"', chunk))
        lat = quick_find(r'"lat":(-?\d+\.\d+)', chunk)
        lon = quick_find(r'"lon":(-?\d+\.\d+)', chunk)
        d_id = quick_find(r'"domain":\{"id":(\d+)', chunk)
        d_name = clean_text(quick_find(r'"domain":\{"id":\d+,"name":"(.*?)"\}', chunk))
        custom_id = quick_find(r'"customId":"(.*?)"', chunk)
        first_data = quick_find(r'"firstData":"(.*?)"', chunk)[:10]
        last_data = quick_find(r'"lastData":"(.*?)"', chunk)[:10]
        granularity = quick_find(r'"granularity":"(.*?)"', chunk)
        directional = quick_find(r'"directional":(true|false)', chunk)
        straat   = quick_find(r'"addressStreet":"(.*?)"', chunk)
        nummer   = quick_find(r'"addressNumber":"(.*?)"', chunk)
        postcode = quick_find(r'"addressPostcode":"(.*?)"', chunk)
        gemeente = quick_find(r'"addressPlace":"(.*?)"', chunk)

        if not lon or float(lon) == 0:
            logger.info("Geocoding voor ID %s...", pid)
            geo_lat, geo_lon = geocodeer(straat, nummer, postcode, gemeente)
            if geo_lat and geo_lon:
                lat, lon = str(geo_lat), str(geo_lon)
            else:
                logger.warning("Geocoding mislukt voor ID %s, telpaal overgeslagen", pid)
                continue

        # Aangepast naar variabelen uit sprint 0 voorbeeld
        resultaten.append({
            "counting_point_id": pid,
            "customId": empty_to_none(custom_id),
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "firstData": first_data.replace("T", " "),
            "lastData": last_data.replace("T", " "),
            "granularity": granularity,
            "directional": directional.capitalize(),
            "domain_id": d_id,
            "domain_name": d_name,
            "description": empty_to_none(description),
            "postcode": postcode
        })
        seen_ids.add(pid)
 
    if not resultaten:
        return pd.DataFrame()
    
    df = pd.DataFrame(resultaten)
    
    logger.info("Richtingsnamen ophalen voor %d telpalen...", len(df))
    for i, row in df.iterrows():
        pid = row['counting_point_id']
        name_in, name_out = haal_richtingsnamen(pid)
        df.at[i, 'direction_name_in'] = empty_to_none(name_in)
        df.at[i, 'direction_name_out'] = empty_to_none(name_out)
        time.sleep(0.1)
        if (i + 1) % 20 == 0:
            logger.info("  %d/%d telpalen verwerkt...", i + 1, len(df))
    return df 

