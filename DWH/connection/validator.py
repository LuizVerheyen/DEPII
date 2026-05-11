# validator.py
#
# Bevat alle herbruikbare checkfuncties en een validatiefunctie per tabel.
# Wordt aangeroepen vanuit initiator.py, fillerTrain.py, factWeather.py
# en fillerVoorAanpassingen.py voor elke load naar de DWH.

import logging
from dataclasses import dataclass, field
import pandas as pd

logger = logging.getLogger(__name__)


# Golfindeling voor de pipeline

# Onafhankelijke dimensies (geen getData()-calls intern)
LOAD_0_TABLES = [
    "DimTime",
    "DimDate",
    "DimLocation",
    "DimTransportType",
    "DimDepartement",
]

# Afhankelijke dimensies (doen getData()-calls op eerder geladen tabellen)
LOAD_1_TABLES = [
    "DimBlueBikeStation",
    "DimStation",
    "DimWeatherStation",
    "DimWorkerMobility",
    "DimCountingPoint",
    "DimStaff",
    "DimStudent",
]

# Feitentabellen (doen getData()-calls op dimensies)
LOAD_2_TABLES = [
    "FactWorkerMobility",
    "FactDepartement",
    "FactStaffCommute",
    "FactCountings",
    "FactStudentMobility",
    "FactMeteo",
]


# Dataclasses voor rapportage

@dataclass
class TableReport:
    table: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    row_count: int = 0


@dataclass
class PipelineReport:
    tables: list[TableReport] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(t.passed for t in self.tables)


# Herbruikbare checkfuncties

def _is_empty(df) -> bool:
    return df is None or (isinstance(df, pd.DataFrame) and df.empty)

def _row_count(df) -> int:
    if df is None:
        return 0
    return len(df)

def check_not_empty(df, table: str) -> list[str]:
    if _is_empty(df):
        return [f"{table}: DataFrame is leeg of None"]
    return []

def check_columns(df, expected: list[str], table: str) -> list[str]:
    if _is_empty(df):
        return []
    missing = [c for c in expected if c not in df.columns]
    return [f"{table}: ontbrekende kolom '{c}'" for c in missing]

def check_no_nulls(df, cols: list[str], table: str) -> list[str]:
    if _is_empty(df):
        return []
    errors = []
    for col in cols:
        if col in df.columns and df[col].isnull().any():
            n = df[col].isnull().sum()
            errors.append(f"{table}: {n} NULL-waarde(n) in verplicht veld '{col}'")
    return errors

def check_no_duplicates(df, key_cols: list[str], table: str) -> list[str]:
    if _is_empty(df):
        return []
    if not all(c in df.columns for c in key_cols):
        return []
    n = df.duplicated(subset=key_cols).sum()
    if n > 0:
        return [f"{table}: {n} dubbele rij(en) op sleutel {key_cols}"]
    return []

def check_no_negatives(df, cols: list[str], table: str) -> list[str]:
    if _is_empty(df):
        return []
    errors = []
    for col in cols:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            n = (df[col].dropna() < 0).sum()
            if n > 0:
                errors.append(f"{table}: {n} negatieve waarde(n) in '{col}'")
    return errors

def check_exact_row_count(df, expected: int, table: str) -> list[str]:
    if _is_empty(df):
        return []
    actual = len(df)
    if actual != expected:
        return [f"{table}: verwacht exact {expected} rijen, maar kreeg {actual}"]
    return []

def check_datekey_format(df, col: str, table: str) -> list[str]:
    """Controleert of een INT-kolom een geldige YYYYMMDD-datum bevat."""
    if _is_empty(df) or col not in df.columns:
        return []
    try:
        pd.to_datetime(df[col].astype(str), format="%Y%m%d")
        return []
    except Exception:
        return [f"{table}: ongeldige YYYYMMDD-waarden in DateKey-kolom '{col}'"]

def check_unique_values(df, col: str, table: str) -> list[str]:
    """Controleert of een kolom alleen unieke waarden bevat (enkelvoudige unique constraint)."""
    if _is_empty(df) or col not in df.columns:
        return []
    n = df.duplicated(subset=[col]).sum()
    if n > 0:
        return [f"{table}: {n} dubbele waarde(n) in unieke kolom '{col}'"]
    return []


# ── Validators per tabel ──────────────────────────────────────────────────────
#
# Elke validator:
#   - neemt een DataFrame
#   - geeft een TableReport terug met passed=True/False en een lijst van foutmeldingen
#
# Wat gecontroleerd wordt en wat niet:
#   - Niet-negatieve waarden: ook gedekt door DDL CHECK constraints, maar hier vroeger
#     afgevangen zodat de foutmelding duidelijker is en de load niet half lukt.
#   - Primaire sleutels / UNIQUE: ook in DDL, maar een laadpoging met dubbels crasht
#     de hele tabel.
#   - Foreign keys: NIET gecontroleerd in Python — dat vereist een live DB-verbinding
#     tijdens validatie. De DDL FK-constraints vangen dit op bij de load.
#   - NOT NULL op surrogaatsleutels (IDENTITY): niet relevant, die genereert SQL zelf.


def validate_dim_time(df) -> TableReport:
    """
    DimTime: 1440 rijen (één per minuut), unieke TimeKey, geen NULL op sleutels.
    Vaste tabel — exact rijgetal gecontroleerd.
    """
    errors = []
    errors += check_not_empty(df, "DimTime")
    if not errors:
        errors += check_columns(df, ["TimeKey", "fullTime", "Hour", "Minute", "AMPM", "Hour12"], "DimTime")
        errors += check_no_duplicates(df, ["TimeKey"], "DimTime")
        errors += check_no_nulls(df, ["TimeKey", "Hour", "Minute"], "DimTime")
        errors += check_no_negatives(df, ["TimeKey", "Hour", "Minute", "Hour12"], "DimTime")
        errors += check_exact_row_count(df, 1440, "DimTime")
    return TableReport("DimTime", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_date(df) -> TableReport:
    """
    DimDate: 6209 rijen (2010-01-01 t/m 2026-12-31), unieke DateKey, geldige YYYYMMDD.
    Vaste tabel — exact rijgetal gecontroleerd.
    """
    errors = []
    errors += check_not_empty(df, "DimDate")
    if not errors:
        errors += check_columns(df, [
            "DateKey", "FullDateAlternateKey", "DayOfMonth", "EnglishDayNameOfWeek",
            "DutchDayNameOfWeek", "DayOfWeek", "DayOfWeekInMonth", "DayOfWeekInYear",
            "DayOfQuarter", "DayOfYear", "WeekOfMonth", "WeekOfQuarter", "WeekOfYear",
            "Month", "EnglishMonthName", "DutchMonthName", "MonthOfQuarter", "Quarter",
            "QuarterName", "Year", "MonthYear", "MMYYYY", "IsHoliday", "HolidayName",
            "IsWeekend", "IsWorkingDay", "IsSchoolHoliday", "SchoolHolidayName"
        ], "DimDate")
        errors += check_no_duplicates(df, ["DateKey"], "DimDate")
        errors += check_no_nulls(df, ["DateKey", "Year", "Month", "DayOfMonth"], "DimDate")
        errors += check_datekey_format(df, "DateKey", "DimDate")
        errors += check_no_negatives(df, ["DateKey", "Year", "Month", "DayOfMonth", "Quarter"], "DimDate")
        errors += check_exact_row_count(df, 6209, "DimDate")
    return TableReport("DimDate", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_location(df) -> TableReport:
    """
    DimLocation: 2764 rijen, geen dubbele (PostalCode, Municipality, MainMunicipality, Province).
    Vaste opzoektabel — exact rijgetal gecontroleerd.
    """
    errors = []
    errors += check_not_empty(df, "DimLocation")
    if not errors:
        errors += check_columns(df, ["PostalCode", "Municipality", "MainMunicipality", "Province"], "DimLocation")
        errors += check_no_duplicates(
            df, ["PostalCode", "Municipality", "MainMunicipality", "Province"], "DimLocation"
        )
        # PostalCode, Municipality en MainMunicipality zijn verplicht; Province mag NULL zijn
        errors += check_no_nulls(df, ["PostalCode", "Municipality", "MainMunicipality"], "DimLocation")
        errors += check_exact_row_count(df, 2764, "DimLocation")
    return TableReport("DimLocation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_transport_type(df) -> TableReport:
    """
    DimTransportType: 8 vaste rijen, unieke VehicleType, geen negatieve CO2PerKM.
    Vaste opzoektabel — exact rijgetal gecontroleerd.
    """
    errors = []
    errors += check_not_empty(df, "DimTransportType")
    if not errors:
        errors += check_columns(df, ["VehicleType", "CO2PerKM"], "DimTransportType")
        errors += check_unique_values(df, "VehicleType", "DimTransportType")
        errors += check_no_nulls(df, ["VehicleType"], "DimTransportType")
        errors += check_no_negatives(df, ["CO2PerKM"], "DimTransportType")
        errors += check_exact_row_count(df, 8, "DimTransportType")
    return TableReport("DimTransportType", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_bluebike_station(df) -> TableReport:
    """
    DimBlueBikeStation: bevat alleen nieuwe stations (mag leeg zijn als er niets nieuws is),
    unieke BlueBikeStationKey, geen NULL op LocationKey/Latitude/Longitude.
    Lege DataFrame is geldig — er zijn gewoon geen nieuwe stations vandaag.
    """
    if _is_empty(df):
        return TableReport("DimBlueBikeStation", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, ["BlueBikeStationKey", "LocationName", "Latitude", "Longitude", "LocationKey"], "DimBlueBikeStation")
    errors += check_no_duplicates(df, ["BlueBikeStationKey"], "DimBlueBikeStation")
    errors += check_no_nulls(df, ["BlueBikeStationKey", "LocationKey", "Latitude", "Longitude"], "DimBlueBikeStation")
    errors += check_no_negatives(df, ["BlueBikeStationKey", "LocationKey"], "DimBlueBikeStation")
    return TableReport("DimBlueBikeStation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_station(df) -> TableReport:
    """
    DimStation: bevat stations nabij Blue-bike locaties, unieke URI,
    geen NULL op URI/StationName/Latitude/Longitude.
    Lege DataFrame is geldig — kan leeg zijn als er geen nieuwe stations zijn.
    """
    if _is_empty(df):
        return TableReport("DimStation", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, ["URI", "StationName", "Latitude", "Longitude", "LocationKey"], "DimStation")
    errors += check_unique_values(df, "URI", "DimStation")
    errors += check_no_nulls(df, ["URI", "StationName", "Latitude", "Longitude"], "DimStation")
    return TableReport("DimStation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_weather_station(df) -> TableReport:
    """
    DimWeatherStation: volledige snapshot (if_exists='replace'), unieke WeatherStationID,
    SnapshotDate aanwezig en niet NULL, numerieke Altitude/Latitude/Longitude.
    """
    errors = []
    errors += check_not_empty(df, "DimWeatherStation")
    if not errors:
        errors += check_columns(df, [
            "WeatherStationID", "Name", "Altitude",
            "Latitude", "Longitude", "Point", "LocationKey", "SnapshotDate"
        ], "DimWeatherStation")
        errors += check_unique_values(df, "WeatherStationID", "DimWeatherStation")
        errors += check_no_nulls(df, ["WeatherStationID", "Latitude", "Longitude", "SnapshotDate"], "DimWeatherStation")
        errors += check_no_negatives(df, ["LocationKey"], "DimWeatherStation")
    return TableReport("DimWeatherStation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_worker_mobility(df) -> TableReport:
    """
    DimWorkerMobility: unieke ResponseID (UNIQUE constraint in DDL),
    geen NULL op ResponseID, geldige RecordDate als YYYYMMDD.
    """
    errors = []
    errors += check_not_empty(df, "DimWorkerMobility")
    if not errors:
        errors += check_columns(df, [
            "RecordDate", "ResponseID", "Latitude", "Longitude", "WorkPlace", "Finished",
            "WorkFunction", "WorkRegime", "HomeWork", "LocationKey"
        ], "DimWorkerMobility")
        errors += check_unique_values(df, "ResponseID", "DimWorkerMobility")
        errors += check_no_nulls(df, ["ResponseID", "RecordDate"], "DimWorkerMobility")
        errors += check_no_negatives(df, ["LocationKey"], "DimWorkerMobility")
        errors += check_datekey_format(df, "RecordDate", "DimWorkerMobility")
    return TableReport("DimWorkerMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_departement(df) -> TableReport:
    """
    DimDepartement: unieke departementnamen met geldige StartDate/EndDate,
    geen NULL op verplichte velden.
    """
    errors = []
    errors += check_not_empty(df, "DimDepartement")
    if not errors:
        errors += check_columns(df, ["DepartementName", "StartDate", "EndDate"], "DimDepartement")
        errors += check_no_nulls(df, ["DepartementName", "StartDate", "EndDate"], "DimDepartement")
        errors += check_unique_values(df, "DepartementName", "DimDepartement")
        errors += check_no_negatives(df, ["StartDate", "EndDate"], "DimDepartement")
        errors += check_datekey_format(df, "StartDate", "DimDepartement")
        errors += check_datekey_format(df, "EndDate", "DimDepartement")
    return TableReport("DimDepartement", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_staff(df) -> TableReport:
    """
    DimStaff: unieke StaffID, geen NULL op StaffID.
    Lege DataFrame is geldig — geen nieuwe medewerkers.
    """
    if _is_empty(df):
        return TableReport("DimStaff", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, ["StaffID", "DepartementKey", "Campus"], "DimStaff")
    errors += check_unique_values(df, "StaffID", "DimStaff")
    errors += check_no_nulls(df, ["StaffID"], "DimStaff")
    errors += check_no_negatives(df, ["DepartementKey"], "DimStaff")
    return TableReport("DimStaff", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_student(df) -> TableReport:
    """
    DimStudent: unieke StudentName, geen NULL op StudentName.
    Lege DataFrame is geldig — geen nieuwe studenten.
    """
    if _is_empty(df):
        return TableReport("DimStudent", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, ["StudentName", "DepartementKey"], "DimStudent")
    errors += check_unique_values(df, "StudentName", "DimStudent")
    errors += check_no_nulls(df, ["StudentName"], "DimStudent")
    errors += check_no_negatives(df, ["DepartementKey"], "DimStudent")
    return TableReport("DimStudent", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_dim_counting_point(df) -> TableReport:
    """
    DimCountingPoint: unieke CountingPointID, geen NULL op CountingPointID en LocationKey.
    Lege DataFrame is geldig — geen nieuwe telpalen.
    """
    if _is_empty(df):
        return TableReport("DimCountingPoint", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, [
        "CountingPointID", "CustomID", "CountingPointName", "Latitude", "Longitude",
        "FirstData", "Granularity", "Directional", "DirectionNameIn", "DirectionNameOut",
        "DomainID", "DomainName", "Description", "LocationKey"
    ], "DimCountingPoint")
    errors += check_no_duplicates(df, ["CountingPointID"], "DimCountingPoint")
    errors += check_no_nulls(df, ["CountingPointID", "LocationKey"], "DimCountingPoint")
    errors += check_no_negatives(df, ["CountingPointID", "DomainID", "LocationKey"], "DimCountingPoint")
    return TableReport("DimCountingPoint", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_meteo(df) -> TableReport:
    """
    FactMeteo: dagelijkse weerdata. Mag None/leeg zijn als de API niets teruggeeft —
    dat is geen fout maar wordt wel gemeld. Logische grain: (WeatherStationKey, DateKey).
    """
    if _is_empty(df):
        # Niet geblokkeerd — API kan legitiem leeg zijn vandaag
        return TableReport("FactMeteo", passed=True, errors=["FactMeteo: geen data ontvangen van API (niet geblokkeerd)"], row_count=0)

    errors = []
    errors += check_columns(df, [
        "WeatherStationKey", "PrecipQuantity", "TempAvg", "TempMax", "TempMin",
        "TempGrassPt100Avg", "TempSoilAvg", "TempSoilAvg5cm", "TempSoilAvg10cm",
        "TempSoilAvg20cm", "TempSoilAvg50cm", "WindSpeed10m", "WindSpeedAvg30m",
        "WindGustsSpeed", "HumidityRelShelterAvg", "Pressure", "SunDuration",
        "ShortWaveFromSkyAvg", "SunIntAvg", "DateKey"
    ], "FactMeteo")
    errors += check_no_nulls(df, ["WeatherStationKey", "DateKey"], "FactMeteo")
    errors += check_no_duplicates(df, ["WeatherStationKey", "DateKey"], "FactMeteo")
    errors += check_no_negatives(df, [
        "PrecipQuantity", "WindSpeed10m", "WindSpeedAvg30m",
        "WindGustsSpeed", "HumidityRelShelterAvg", "Pressure",
        "SunDuration", "ShortWaveFromSkyAvg", "SunIntAvg"
    ], "FactMeteo")
    errors += check_datekey_format(df, "DateKey", "FactMeteo")
    return TableReport("FactMeteo", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_bluebike(df) -> TableReport:
    """
    FactBlueBike: samengestelde PK (BlueBikeStationKey, DateKey, TimeKey),
    geen NULL op die drie kolommen, geen negatieve telwaarden.
    """
    errors = []
    errors += check_not_empty(df, "FactBlueBike")
    if not errors:
        errors += check_columns(df, [
            "BlueBikeStationKey", "TotalBikesAvailable", "EBikesAvailable",
            "BlueBikesAvailable", "MaxCapacity", "BikesDefect", "BikesInUse",
            "DateKey", "TimeKey", "LinkedStationKey"
        ], "FactBlueBike")
        errors += check_no_duplicates(df, ["BlueBikeStationKey", "DateKey", "TimeKey"], "FactBlueBike")
        errors += check_no_nulls(df, ["BlueBikeStationKey", "DateKey", "TimeKey"], "FactBlueBike")
        errors += check_no_negatives(df, [
            "BlueBikeStationKey", "DateKey", "TimeKey",
            "TotalBikesAvailable", "EBikesAvailable", "BlueBikesAvailable",
            "MaxCapacity", "BikesDefect", "BikesInUse", "LinkedStationKey"
        ], "FactBlueBike")
        errors += check_datekey_format(df, "DateKey", "FactBlueBike")
    return TableReport("FactBlueBike", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_worker_mobility(df) -> TableReport:
    """
    FactWorkerMobility: geen NULL op WorkerID en Datekey, geen negatieve TotalEmission.
    TransportKey mag NULL zijn (wanneer TravelName niet ingevuld is in de bron).
    """
    errors = []
    errors += check_not_empty(df, "FactWorkerMobility")
    if not errors:
        errors += check_columns(df, ["WorkerID", "Datekey", "TransportKey", "TravelTime", "TravelDistance", "TotalEmission"], "FactWorkerMobility")
        # TransportKey mag NULL zijn - alleen WorkerID en Datekey zijn verplicht
        errors += check_no_nulls(df, ["WorkerID", "Datekey"], "FactWorkerMobility")
        errors += check_no_negatives(df, ["TravelTime", "TravelDistance", "TotalEmission"], "FactWorkerMobility")
        # TransportKey mag NULL zijn, maar als niet-NULL moet het positief zijn
        if "TransportKey" in df.columns:
            invalid_transport = df[(df["TransportKey"].notna()) & (df["TransportKey"] < 0)]
            if len(invalid_transport) > 0:
                errors.append(f"FactWorkerMobility: {len(invalid_transport)} ongeldige negatieve TransportKey waarde(n)")
    return TableReport("FactWorkerMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_departement(df) -> TableReport:
    """
    FactDepartement: samengestelde PK (DateKey, DepartementKey), geldige DateKey,
    geen negatieve AmountOfWorkers.
    """
    errors = []
    errors += check_not_empty(df, "FactDepartement")
    if not errors:
        errors += check_columns(df, ["DateKey", "DepartementKey", "AmountOfWorkers"], "FactDepartement")
        errors += check_no_duplicates(df, ["DateKey", "DepartementKey"], "FactDepartement")
        errors += check_no_nulls(df, ["DateKey", "DepartementKey"], "FactDepartement")
        errors += check_no_negatives(df, ["DateKey", "DepartementKey", "AmountOfWorkers"], "FactDepartement")
        errors += check_datekey_format(df, "DateKey", "FactDepartement")
    return TableReport("FactDepartement", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_staff_commute(df) -> TableReport:
    """
    FactStaffCommute: geen NULL op StaffKey/DateKey, geen negatieve DistanceKM,
    geldige DateKey.
    """
    errors = []
    errors += check_not_empty(df, "FactStaffCommute")
    if not errors:
        errors += check_columns(df, ["StaffKey", "DateKey", "Period", "DistanceKM"], "FactStaffCommute")
        errors += check_no_nulls(df, ["StaffKey", "DateKey"], "FactStaffCommute")
        errors += check_no_negatives(df, ["StaffKey", "DateKey", "DistanceKM"], "FactStaffCommute")
        errors += check_datekey_format(df, "DateKey", "FactStaffCommute")
    return TableReport("FactStaffCommute", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_countings(df) -> TableReport:
    """
    FactCountings: samengestelde PK (CountingPointID, DateKey), geen negatieve telwaarden,
    geldige DateKey.
    Lege DataFrame is geldig — geen nieuwe tellingen vandaag.
    """
    if _is_empty(df):
        return TableReport("FactCountings", passed=True, errors=[], row_count=0)

    errors = []
    errors += check_columns(df, [
        "CountingPointID", "DateKey", "DirectionInCounts", "DirectionOutCounts", "TotalCounts"
    ], "FactCountings")
    errors += check_no_duplicates(df, ["CountingPointID", "DateKey"], "FactCountings")
    errors += check_no_nulls(df, ["CountingPointID", "DateKey"], "FactCountings")
    errors += check_no_negatives(df, ["DirectionInCounts", "DirectionOutCounts", "TotalCounts"], "FactCountings")
    errors += check_datekey_format(df, "DateKey", "FactCountings")
    return TableReport("FactCountings", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_student_mobility(df) -> TableReport:
    """
    FactStudentMobility: geen NULL op StudentKey/DateKey/TransportKey,
    geen negatieve DistanceKM, geldige DateKey.
    """
    errors = []
    errors += check_not_empty(df, "FactStudentMobility")
    if not errors:
        errors += check_columns(df, ["StudentKey", "DateKey", "TransportKey", "DistanceKM"], "FactStudentMobility")
        errors += check_no_nulls(df, ["StudentKey", "DateKey"], "FactStudentMobility")
        errors += check_no_negatives(df, ["StudentKey", "DateKey", "DistanceKM"], "FactStudentMobility")
        # TransportKey mag NULL zijn, maar als niet-NULL moet het positief zijn
        if "TransportKey" in df.columns:
            invalid_transport = df[(df["TransportKey"].notna()) & (df["TransportKey"] < 0)]
            if len(invalid_transport) > 0:
                errors.append(f"FactStudentMobility: {len(invalid_transport)} ongeldige negatieve TransportKey waarde(n)")
        errors += check_datekey_format(df, "DateKey", "FactStudentMobility")
    return TableReport("FactStudentMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def validate_fact_train_arrival(df) -> TableReport:
    """
    FactTrainArrival: samengestelde PK (StationKey, DateKey, StartTime),
    StartTime moet strikt kleiner zijn dan EndTime, geen negatieve AmountOfArrivals.
    """
    errors = []
    errors += check_not_empty(df, "FactTrainArrival")
    if not errors:
        errors += check_columns(df, [
            "StationKey", "DateKey", "StartTime", "EndTime", "AmountOfArrivals"
        ], "FactTrainArrival")
        errors += check_no_duplicates(df, ["StationKey", "DateKey", "StartTime"], "FactTrainArrival")
        errors += check_no_nulls(df, ["StationKey", "DateKey", "StartTime", "EndTime"], "FactTrainArrival")
        errors += check_no_negatives(df, ["StationKey", "DateKey", "StartTime", "EndTime", "AmountOfArrivals"], "FactTrainArrival")
        errors += check_datekey_format(df, "DateKey", "FactTrainArrival")
        # StartTime moet altijd kleiner zijn dan EndTime
        if "StartTime" in df.columns and "EndTime" in df.columns:
            invalid = (
                (df["StartTime"] >= df["EndTime"]) &
                ~( (df["StartTime"] == 2330) & (df["EndTime"] == 0) )
            ).sum()
            if invalid > 0:
                errors.append(f"FactTrainArrival: {invalid} rij(en) waarbij StartTime >= EndTime")
    return TableReport("FactTrainArrival", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))

# validate bij update
def update_validate_dim_time(df) -> TableReport:
    """
    DimTime: 1440 rijen (één per minuut), unieke TimeKey, geen NULL op sleutels.
    Vaste tabel — exact rijgetal gecontroleerd.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["TimeKey", "fullTime", "Hour", "Minute", "AMPM", "Hour12"], "DimTime")
        errors += check_no_duplicates(df, ["TimeKey"], "DimTime")
        errors += check_no_nulls(df, ["TimeKey", "Hour", "Minute"], "DimTime")
        errors += check_no_negatives(df, ["TimeKey", "Hour", "Minute", "Hour12"], "DimTime")
        errors += check_exact_row_count(df, 1440, "DimTime")
    return TableReport("DimTime", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_dim_date(df) -> TableReport:
    """
    DimDate: 6209 rijen (2010-01-01 t/m 2026-12-31), unieke DateKey, geldige YYYYMMDD.
    Vaste tabel — exact rijgetal gecontroleerd.
    """
    errors = []
    if not errors:
        errors += check_columns(df, [
            "DateKey", "FullDateAlternateKey", "DayOfMonth", "EnglishDayNameOfWeek",
            "DutchDayNameOfWeek", "DayOfWeek", "DayOfWeekInMonth", "DayOfWeekInYear",
            "DayOfQuarter", "DayOfYear", "WeekOfMonth", "WeekOfQuarter", "WeekOfYear",
            "Month", "EnglishMonthName", "DutchMonthName", "MonthOfQuarter", "Quarter",
            "QuarterName", "Year", "MonthYear", "MMYYYY", "IsHoliday", "HolidayName",
            "IsWeekend", "IsWorkingDay", "IsSchoolHoliday", "SchoolHolidayName"
        ], "DimDate")
        errors += check_no_duplicates(df, ["DateKey"], "DimDate")
        errors += check_no_nulls(df, ["DateKey", "Year", "Month", "DayOfMonth"], "DimDate")
        errors += check_datekey_format(df, "DateKey", "DimDate")
        errors += check_no_negatives(df, ["DateKey", "Year", "Month", "DayOfMonth", "Quarter"], "DimDate")
        errors += check_exact_row_count(df, 6209, "DimDate")
    return TableReport("DimDate", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_dim_location(df) -> TableReport:
    """
    DimLocation: 2764 rijen, geen dubbele (PostalCode, Municipality, MainMunicipality, Province).
    Vaste opzoektabel — exact rijgetal gecontroleerd.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["PostalCode", "Municipality", "MainMunicipality", "Province"], "DimLocation")
        errors += check_no_duplicates(
            df, ["PostalCode", "Municipality", "MainMunicipality", "Province"], "DimLocation"
        )
        # PostalCode, Municipality en MainMunicipality zijn verplicht; Province mag NULL zijn
        errors += check_no_nulls(df, ["PostalCode", "Municipality", "MainMunicipality"], "DimLocation")
    return TableReport("DimLocation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_dim_transport_type(df) -> TableReport:
    """
    DimTransportType: 8 vaste rijen, unieke VehicleType, geen negatieve CO2PerKM.
    Vaste opzoektabel — exact rijgetal gecontroleerd.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["VehicleType", "CO2PerKM"], "DimTransportType")
        errors += check_unique_values(df, "VehicleType", "DimTransportType")
        errors += check_no_nulls(df, ["VehicleType"], "DimTransportType")
        errors += check_no_negatives(df, ["CO2PerKM"], "DimTransportType")
        errors += check_exact_row_count(df, 8, "DimTransportType")
    return TableReport("DimTransportType", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))

def update_validate_dim_weather_station(df) -> TableReport:
    """
    DimWeatherStation: volledige snapshot (if_exists='replace'), unieke WeatherStationID,
    SnapshotDate aanwezig en niet NULL, numerieke Altitude/Latitude/Longitude.
    """
    errors = []
    if not errors:
        errors += check_columns(df, [
            "WeatherStationID", "Name", "Altitude",
            "Latitude", "Longitude", "Point", "LocationKey", "SnapshotDate"
        ], "DimWeatherStation")
        errors += check_unique_values(df, "WeatherStationID", "DimWeatherStation")
        errors += check_no_nulls(df, ["WeatherStationID", "Latitude", "Longitude", "SnapshotDate"], "DimWeatherStation")
        errors += check_no_negatives(df, ["LocationKey"], "DimWeatherStation")
    return TableReport("DimWeatherStation", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_dim_worker_mobility(df) -> TableReport:
    """
    DimWorkerMobility: unieke ResponseID (UNIQUE constraint in DDL),
    geen NULL op ResponseID, geldige RecordDate als YYYYMMDD.
    """
    errors = []
    if not errors:
        errors += check_columns(df, [
            "RecordDate", "ResponseID", "Latitude", "Longitude", "WorkPlace", "Finished",
            "WorkFunction", "WorkRegime", "HomeWork", "LocationKey"
        ], "DimWorkerMobility")
        errors += check_unique_values(df, "ResponseID", "DimWorkerMobility")
        errors += check_no_nulls(df, ["ResponseID", "RecordDate"], "DimWorkerMobility")
        errors += check_no_negatives(df, ["LocationKey"], "DimWorkerMobility")
        errors += check_datekey_format(df, "RecordDate", "DimWorkerMobility")
    return TableReport("DimWorkerMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_dim_departement(df) -> TableReport:
    """
    DimDepartement: unieke departementnamen met geldige StartDate/EndDate,
    geen NULL op verplichte velden.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["DepartementName", "StartDate", "EndDate"], "DimDepartement")
        errors += check_no_nulls(df, ["DepartementName", "StartDate", "EndDate"], "DimDepartement")
        errors += check_unique_values(df, "DepartementName", "DimDepartement")
        errors += check_no_negatives(df, ["StartDate", "EndDate"], "DimDepartement")
        errors += check_datekey_format(df, "StartDate", "DimDepartement")
        errors += check_datekey_format(df, "EndDate", "DimDepartement")
    return TableReport("DimDepartement", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))

def update_validate_fact_worker_mobility(df) -> TableReport:
    """
    FactWorkerMobility: geen NULL op WorkerID en Datekey, geen negatieve TotalEmission.
    TransportKey mag NULL zijn (wanneer TravelName niet ingevuld is in de bron).
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["WorkerID", "Datekey", "TransportKey", "TravelTime", "TravelDistance", "TotalEmission"], "FactWorkerMobility")
        # TransportKey mag NULL zijn - alleen WorkerID en Datekey zijn verplicht
        errors += check_no_nulls(df, ["WorkerID", "Datekey"], "FactWorkerMobility")
        errors += check_no_negatives(df, ["TravelTime", "TravelDistance", "TotalEmission"], "FactWorkerMobility")
        # TransportKey mag NULL zijn, maar als niet-NULL moet het positief zijn
        if "TransportKey" in df.columns:
            invalid_transport = df[(df["TransportKey"].notna()) & (df["TransportKey"] < 0)]
            if len(invalid_transport) > 0:
                errors.append(f"FactWorkerMobility: {len(invalid_transport)} ongeldige negatieve TransportKey waarde(n)")
    return TableReport("FactWorkerMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_fact_departement(df) -> TableReport:
    """
    FactDepartement: samengestelde PK (DateKey, DepartementKey), geldige DateKey,
    geen negatieve AmountOfWorkers.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["DateKey", "DepartementKey", "AmountOfWorkers"], "FactDepartement")
        errors += check_no_duplicates(df, ["DateKey", "DepartementKey"], "FactDepartement")
        errors += check_no_nulls(df, ["DateKey", "DepartementKey"], "FactDepartement")
        errors += check_no_negatives(df, ["DateKey", "DepartementKey", "AmountOfWorkers"], "FactDepartement")
        errors += check_datekey_format(df, "DateKey", "FactDepartement")
    return TableReport("FactDepartement", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


def update_validate_fact_staff_commute(df) -> TableReport:
    """
    FactStaffCommute: geen NULL op StaffKey/DateKey, geen negatieve DistanceKM,
    geldige DateKey.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["StaffKey", "DateKey", "Period", "DistanceKM"], "FactStaffCommute")
        errors += check_no_nulls(df, ["StaffKey", "DateKey"], "FactStaffCommute")
        errors += check_no_negatives(df, ["StaffKey", "DateKey", "DistanceKM"], "FactStaffCommute")
        errors += check_datekey_format(df, "DateKey", "FactStaffCommute")
    return TableReport("FactStaffCommute", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))

def update_validate_fact_student_mobility(df) -> TableReport:
    """
    FactStudentMobility: geen NULL op StudentKey/DateKey/TransportKey,
    geen negatieve DistanceKM, geldige DateKey.
    """
    errors = []
    if not errors:
        errors += check_columns(df, ["StudentKey", "DateKey", "TransportKey", "DistanceKM"], "FactStudentMobility")
        errors += check_no_nulls(df, ["StudentKey", "DateKey"], "FactStudentMobility")
        errors += check_no_negatives(df, ["StudentKey", "DateKey", "DistanceKM"], "FactStudentMobility")
        # TransportKey mag NULL zijn, maar als niet-NULL moet het positief zijn
        if "TransportKey" in df.columns:
            invalid_transport = df[(df["TransportKey"].notna()) & (df["TransportKey"] < 0)]
            if len(invalid_transport) > 0:
                errors.append(f"FactStudentMobility: {len(invalid_transport)} ongeldige negatieve TransportKey waarde(n)")
        errors += check_datekey_format(df, "DateKey", "FactStudentMobility")
    return TableReport("FactStudentMobility", passed=len(errors) == 0, errors=errors, row_count=_row_count(df))


# Mapping: tabelnaam → validatiefunctie

VALIDATORS: dict = {
    "DimTime":             validate_dim_time,
    "DimDate":             validate_dim_date,
    "DimLocation":         validate_dim_location,
    "DimTransportType":    validate_dim_transport_type,
    "DimBlueBikeStation":  validate_dim_bluebike_station,
    "DimStation":          validate_dim_station,
    "DimWeatherStation":   validate_dim_weather_station,
    "DimWorkerMobility":   validate_dim_worker_mobility,
    "DimDepartement":      validate_dim_departement,
    "DimStaff":            validate_dim_staff,
    "DimStudent":          validate_dim_student,
    "DimCountingPoint":    validate_dim_counting_point,
    "FactMeteo":           validate_fact_meteo,
    "FactBlueBike":        validate_fact_bluebike,
    "FactWorkerMobility":  validate_fact_worker_mobility,
    "FactDepartement":     validate_fact_departement,
    "FactStaffCommute":    validate_fact_staff_commute,
    "FactCountings":       validate_fact_countings,
    "FactStudentMobility": validate_fact_student_mobility,
    "FactTrainArrival":    validate_fact_train_arrival,
}

UPDATE_VALIDATORS: dict = {
    "DimTime":             update_validate_dim_time,
    "DimDate":             update_validate_dim_date,
    "DimLocation":         update_validate_dim_location,
    "DimTransportType":    update_validate_dim_transport_type,
    "DimBlueBikeStation":  validate_dim_bluebike_station,
    "DimStation":          validate_dim_station,
    "DimWeatherStation":   update_validate_dim_weather_station,
    "DimWorkerMobility":   update_validate_dim_worker_mobility,
    "DimDepartement":      update_validate_dim_departement,
    "DimStaff":            validate_dim_staff,
    "DimStudent":          validate_dim_student,
    "DimCountingPoint":    validate_dim_counting_point,
    "FactWorkerMobility":  update_validate_fact_worker_mobility,
    "FactDepartement":     update_validate_fact_departement,
    "FactStaffCommute":    update_validate_fact_staff_commute,
    "FactStudentMobility": update_validate_fact_student_mobility
}


# Hoofdfuncties

def validate_wave(candidates: dict, wave: str) -> "PipelineReport":
    """
    Valideert de tabellen voor een specifieke golf (load_0, load_1 of load_2).
    """
    report = PipelineReport()

    if wave == "load_0":
        tables = LOAD_0_TABLES
    elif wave == "load_1":
        tables = LOAD_1_TABLES
    elif wave == "load_2":
        tables = LOAD_2_TABLES
    else:
        raise ValueError(f"Onbekende golf: '{wave}'. Gebruik 'load_0', 'load_1' of 'load_2'.")

    for table_name in tables:
        if table_name in VALIDATORS:
            df = candidates.get(table_name)
            report.tables.append(VALIDATORS[table_name](df))

    return report


def validate_all(candidates: dict) -> "PipelineReport":
    """
    Valideert alle aanwezige kandidaattabellen.
    Tabellen die niet in `candidates` zitten worden overgeslagen.
    """
    report = PipelineReport()
    for table_name, validator_fn in VALIDATORS.items():
        if table_name in candidates:
            df = candidates[table_name]
            report.tables.append(validator_fn(df))
    return report


def validate_subset(candidates: dict, table_names: list[str]) -> "PipelineReport":
    """
    Valideert alleen de opgegeven tabellen. Handig voor de losse filler-scripts
    die maar één of twee tabellen laden (fillerTrain.py, factWeather.py, ...).
    """
    report = PipelineReport()
    for table_name in table_names:
        if table_name not in VALIDATORS:
            continue
        df = candidates.get(table_name)
        report.tables.append(VALIDATORS[table_name](df))
    return report

def validate_update(candidates: dict) -> "PipelineReport":
    report = PipelineReport()
    for table_name, validator_fn in UPDATE_VALIDATORS.items():
        if table_name in candidates:
            df = candidates[table_name]
            report.tables.append(validator_fn(df))
    return report


def print_report(report: "PipelineReport") -> None:
    """Logt een leesbaar overzicht van het validatierapport."""
    logger.info("── Validatierapport ──────────────────────────────────────────────")
    for t in report.tables:
        status = " OK  " if t.passed else " FOUT"
        logger.info("  [%s] %-25s (%d rijen)", status, t.table, t.row_count)
        for e in t.errors:
            logger.warning("           ! %s", e)
    overall = "GESLAAGD" if report.all_passed else "GEFAALD — niets geladen"
    logger.info("── Resultaat: %s %s\n", overall, "─" * 30)