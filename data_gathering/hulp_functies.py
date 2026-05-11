import logging
from datetime import datetime
import re
import time
import numpy as np
import pandas as pd
import requests

from DWH.connection.connect import getData, get_engine

logger = logging.getLogger(__name__)

engine = get_engine()

def get_vlaanderen_data(lat, lon):
    url = f"https://geo.api.vlaanderen.be/geolocation/v4/Location?latlon={lat},{lon}"
    try:
        r = requests.get(url, timeout=5)
        res = r.json().get('LocationResult', [])
        if res:
            return str(res[0].get('Zipcode'))
    except Exception as e:
        logger.warning("Vlaanderen API call mislukt: %s", e)
    return None

def get_nominatim_data(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&layer=address"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "dep2526g09@gmail.com"})
        time.sleep(1.6)
        res = r.json().get('address', {})
        if res:
            pc = res.get('postcode')
            municipality = res.get('village') or res.get('town') or res.get('city_district') or res.get('city') # or res.get('suburb')
            return str(pc), str(municipality)
    except Exception as e:
        logger.warning("Nominatim API call mislukt: %s", e)
    return None, None

def find_gemeente_in_location(location, locaties):
    location_lower = location.lower()
    for gemeente in locaties:
        if gemeente.lower() in location_lower:
            return gemeente
        # Check elk woord/deel van de gemeentenaam apart
        for deel in re.split(r'[-\s]', gemeente):
            if deel.lower() in location_lower:
                return gemeente
    return None

# Haversine formule
def check_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))

def get_date_key(dt: datetime) -> int:
    return int(dt.strftime('%Y%m%d'))


def get_time_key(dt: datetime) -> int:
    return int(f"{dt.hour:02d}{dt.minute:02d}")

def get_datetime_from_unix(unix_ts: int) -> datetime:
    return datetime.fromtimestamp(unix_ts)

def timekey_datekey_to_datetime(datekey: int, timekey: int) -> datetime:
    return datetime.strptime(f"{datekey}{timekey:04d}", '%Y%m%d%H%M')


def getLocationKey(lat, lon, locatieNaam=None):
    dim_location = getData(engine, query="SELECT * FROM DimLocation")
    
    pc = get_vlaanderen_data(lat, lon)
    match = pd.DataFrame()

    if pc and dim_location is not None and not dim_location.empty:
        match = dim_location[dim_location['PostalCode'] == pc]

    if len(match) == 1:
        municipality = str(match.iloc[0]['Municipality'])
    else:
        pc, municipality = get_nominatim_data(lat, lon)

    if not municipality:
        logger.warning("Geen municipality gevonden voor pc=%s", pc)
        return None
    
    municipality = municipality.title()
    matchLocation = pd.DataFrame()

    if dim_location is not None and not dim_location.empty:
        matchLocation = dim_location[(dim_location['PostalCode'] == pc) & (dim_location['Municipality'] == municipality)]

    # als postcode en municipality niet matchen, zoek dan enkel op municipality
    if matchLocation.empty and dim_location is not None and not dim_location.empty:
        matchLocation = dim_location[dim_location['Municipality'] == municipality]

    # Geen match op municipality, zoek juiste Municipality met locatie naam
    if matchLocation.empty and locatieNaam and not match.empty:
        try:
            municipality = find_gemeente_in_location(
                locatieNaam,
                locaties=match['Municipality'].tolist()
            )
            if dim_location is not None:
                matchLocation = dim_location[dim_location['Municipality'] == municipality.title()]
        except Exception:
            pass

    if not matchLocation.empty:
        return matchLocation.iloc[0].LocationKey

    # laatste falback, kijk alleen naar postcode en neem de eerste
    matchLocation = dim_location[dim_location['PostalCode'] == pc]
    if not matchLocation.empty:
        return matchLocation.iloc[0].LocationKey
    
    logger.warning("Geen LocationKey gevonden: pc=%s, loc=%s, mun=%s, lat=%s, lon=%s", pc, locatieNaam, municipality, lat, lon)
    return None


def filterNewRows(df, table, key_cols):
    if isinstance(key_cols, str):
        key_cols = [key_cols]

    cols = ", ".join(key_cols)
    existing = getData(engine, query=f"SELECT {cols} FROM {table}")

    if existing is None or existing.empty:
        return df

    df_key = df[key_cols].fillna("").astype(str).agg("|".join, axis=1)
    existing_key = existing[key_cols].fillna("").astype(str).agg("|".join, axis=1)

    return (
        df[~df_key.isin(existing_key)]
        .copy()
        .reset_index(drop=True)
    )