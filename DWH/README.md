# DEPI Data Warehouse

Data Warehouse voor het HOGENT Mobiliteitsproject. De DWH verzamelt dagelijks data van externe bronnen (API's, CSV- en Excel-bestanden), transformeert die naar een sterschema en laadt ze in een Microsoft SQL Server database via een gefaseerde ETL-pipeline.

---

## Inhoudsopgave

1. [Mappenstructuur](#mappenstructuur)
2. [Gebruikte technologieën](#gebruikte-technologieën)
3. [Schema](#schema)
   - [Architectuur](#architectuur)
   - [Dimensietabellen](#dimensietabellen)
   - [Feitentabellen](#feitentabellen)
   - [Staging](#staging)
4. [Installatie en configuratie](#installatie-en-configuratie)
5. [Pipeline draaien](#pipeline-draaien)
6. [Pipeline architectuur](#pipeline-architectuur)
   - [Overzicht van de fasen](#overzicht-van-de-fasen)
   - [Afhankelijkheidsketen](#afhankelijkheidsketen)
   - [Intern mechanisme per blok](#intern-mechanisme-per-blok)
7. [Fase 1 — Basislaag](#fase-1--basislaag)
8. [Fase 2a — DimBlueBikeStation](#fase-2a--dimbluebikestation)
9. [Fase 2b — DB-afhankelijke dimensies](#fase-2b--db-afhankelijke-dimensies)
10. [Fase 3 — Feitentabellen](#fase-3--feitentabellen)
11. [Standalone fillers](#standalone-fillers)
12. [Validatie](#validatie)
13. [DDL-constraints als laatste vangnet](#ddl-constraints-als-laatste-vangnet)
14. [Validatiesamenvatting per tabel](#validatiesamenvatting-per-tabel)
15. [Automatische scheduling](#automatische-scheduling-cron-op-de-vm)
16. [Bekende beperkingen](#bekende-beperkingen)

---

## Mappenstructuur

```text
DWH/
├── README.md                       # Deze documentatie
├── ddl schema/
│   └── DDL.sql                     # Volledig DDL-script (database + alle tabellen)
└── connection/
    ├── connect.py                  # Database-verbinding + load/read/delete
    ├── initiator.py                # Hoofdpipeline (4 fasen)
    ├── validator.py                # Pre-load validatie voor alle tabellen
    ├── factWeather.py              # Standalone filler: FactMeteo
    ├── fillerBluebikeStation.py    # Standalone filler: FactBlueBike
    ├── fillerCountingPoints.py     # Standalone filler: DimCountingPoint + FactCountings
    ├── fillerTrain.py              # Standalone filler: FactTrainArrival (staging → fact)
    └── fillerVoorAanpassingen.py   # Standalone filler: FactMeteo (identiek aan factWeather.py)
```

---

## Gebruikte technologieën

| Bibliotheek | Doel |
| --- | --- |
| `pandas` | Core DataFrame-verwerkingslogica; alle kandidaat-DataFrames zijn pandas DataFrames |
| `SQLAlchemy` + `pyodbc` | Database-verbinding en `to_sql()`-laadmethode naar SQL Server |
| `python-dotenv` | Laden van omgevingsvariabelen uit `.env` |
| `requests` | HTTP-calls naar externe API's (Telraam, Blue-bike, VMM, iRail, Nager.at, OpenHolidays) |
| `dataclasses` | `TableReport` en `PipelineReport` in `validator.py` (stdlib, geen installatie nodig) |

---

## Schema

### Architectuur

Het DWH is ontworpen als een **Fact Constellation**: meerdere feitentabellen die gebruikmaken van gedeelde conformed dimensions zoals `DimDate` en `DimTime`.

![Star Schema](../images/dep_starschema.drawio.png)

Het volledige DDL-script staat in [ddl schema/DDL.sql](ddl%20schema/DDL.sql). Voer dit script eenmalig uit op SQL Server om de database en alle tabellen aan te maken.

**Kenmerken:**

- Surrogaatsleutels via `IDENTITY` op alle dimensietabellen
- `FOREIGN KEY`-constraints op alle feitentabellen naar hun dimensies
- `CHECK CONSTRAINT` op alle tabellen voor niet-negatieve waarden
- `UNIQUE`-constraints op kandidaat-sleutels (postcode-combinaties, URI's, coördinaten)
- Taalconventie: Engelstalige tabel- en kolomnamen

### Dimensietabellen

| Tabel | Bron | Beschrijving |
| --- | --- | --- |
| `DimDate` | API (feestdagen, schoolvakanties) | 6209 datums (2010–2026), hiërarchie dag → maand → kwartaal → jaar |
| `DimTime` | Python-logica | 1440 minuten per dag (00:00–23:59), uur, AM/PM |
| `DimLocation` | Excel (vaste bronfile) | 2764 Belgische postcodes met gemeente, hoofdgemeente en provincie |
| `DimTransportType` | CSV | 8 transportmiddelen met CO2-uitstoot per kilometer |
| `DimDepartement` | Excel (via e-mail) | Departementen per maand/jaar |
| `DimStaff` | CSV | Personeelsleden gekoppeld aan departement |
| `DimStudent` | CSV (mobiliteitsbevraging) | Studenten met pendeltijd, vervoermiddel en locatie |
| `DimWorkerMobility` | CSV (mobiliteitsbevraging) | HOGENT-medewerkers met reisafstand, -tijd en vervoertype |
| `DimCountingPoint` | Telraam API | Fietstellingspalen met naam, coördinaten en LocationKey |
| `DimWeatherStation` | VMM CSV-API | Automatische weerstations met coördinaten en hoogte (snapshot) |
| `DimBlueBikeStation` | Blue-bike JSON API | Blue Bike-locaties met coördinaten en LocationKey |
| `DimStation` | iRail CSV | NMBS-stations gefilterd op nabijheid van Blue Bike-stations |

### Feitentabellen

| Tabel | Granulariteit | Gekoppelde dimensies |
| --- | --- | --- |
| `FactCountings` | Telpaal × dag | `DimCountingPoint`, `DimDate` |
| `FactMeteo` | Weerstation × dag | `DimWeatherStation`, `DimDate`, `DimTime` |
| `FactBlueBike` | Station × dag × tijdstip | `DimBlueBikeStation`, `DimDate`, `DimTime`, `DimStation` |
| `FactStaffCommute` | Personeelslid × dag | `DimStaff`, `DimDate` |
| `FactWorkerMobility` | Respondent × datum × transport | `DimWorkerMobility`, `DimDate`, `DimTransportType` |
| `FactDepartement` | Departement × maand | `DimDepartement`, `DimDate` |
| `FactStudentMobility` | Student × datum × transport | `DimStudent`, `DimDate`, `DimTransportType` |
| `FactTrainArrival` | Station × dag × vertrektijd | `DimStation`, `DimDate` |

### Staging

| Tabel | Doel |
| --- | --- |
| `stg_FactTrainArrival` | Buffer voor treindata; stabiele records worden gepromoveerd naar `FactTrainArrival` |

---

## Installatie en configuratie

### 1. Database aanmaken

Voer het DDL-script eenmalig uit op SQL Server:

```bash
sqlcmd -S 127.0.0.1 -U sa -P "<wachtwoord>" -d master -i "DWH/ddl schema/DDL.sql"
```

### 2. Omgevingsvariabelen (.env)

Maak een `.env`-bestand aan in de projectwortel:

```env
DB_SERVER=127.0.0.1,1433
DB_NAME=DEPI
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_USER=sa
databasePWD=<jouw_wachtwoord>
```

### 3. Dependencies

```bash
pip install -r requirements.txt
```

---

## Pipeline draaien

De hoofdpipeline draait alle 4 fasen sequentieel:

```bash
python -m DWH.connection.initiator
```

Of via de Web API (asynchroon in achtergrond-thread):

```bash
curl -X POST http://localhost:5000/api/v1/dwh/refresh
```

De pipeline stopt automatisch als een validatiefase faalt — er wordt dan niets naar de database geschreven voor die fase.

---

## Automatische scheduling (cron op de VM)

De data wordt automatisch opgehaald via cron jobs op de Ubuntu VM. Elke job gebruikt `flock` om te voorkomen dat twee processen gelijktijdig draaien.

| Datasource | Script | Interval | Cron-expressie |
| --- | --- | --- | --- |
| Blue-Bike (weekdag piekuur) | `DWH.connection.fillerBluebikeStation` | Elke 5 min (07:00–09:55 en 16:00–18:55) | `*/5 7-9,16-18 * * 1-5` |
| Blue-Bike (weekdag daluur) | `DWH.connection.fillerBluebikeStation` | Elk uur (overige uren) | `0 0-6,10-15,19-23 * * 1-5` |
| Blue-Bike (weekend) | `DWH.connection.fillerBluebikeStation` | Elk uur | `0 * * * 6,0` |
| Treindata | `DWH.connection.fillerTrain` | Elke 30 minuten (op :01 en :31) | `1,31 * * * *` |
| Weerdata | `DWH.connection.factWeather` | Dagelijks om middernacht | `0 0 * * *` |
| Telpalen | `DWH.connection.fillerCountingPoints` | Wekelijks op maandag om 00:02 | `2 0 * * 1` |

**Motivatie per interval:**

- **Blue-Bike piekuren (elke 5 min):** de bezettingsstatus verandert het snelst tijdens ochtend- en avondspits; hogere granulariteit verhoogt de analytische waarde.
- **Treindata (elke 30 min):** het iRail liveboard toont aankomsten per half uur; `round_down_30()` in `fillerTrain.py` rondt tijdstippen af op het juiste halfuur.
- **Weerdata (dagelijks):** VMM levert gisteren-data als dagaggregaat; meer dan één keer per dag ophalen geeft geen nieuwe records.
- **Telpalen (wekelijks):** de Telraam API levert weekaggregaten; dagelijks ophalen levert geen extra datapunten op.

---

## Pipeline architectuur

### Overzicht van de fasen

```text
┌─────────────────────────────────────────────────────────┐
│  Fase 1   │  Basislaag (geen DB-afhankelijkheden)        │
│           │  DimTime, DimDate, DimLocation,              │
│           │  DimTransportType, DimDepartement,           │
│           │  DimStaff, DimStudent                        │
├─────────────────────────────────────────────────────────┤
│  Fase 2a  │  DimBlueBikeStation                          │
│           │  (nodig vóór DimStation in fase 2b)          │
├─────────────────────────────────────────────────────────┤
│  Fase 2b  │  DB-afhankelijke dimensies                   │
│           │  DimWeatherStation, DimStation,              │
│           │  DimWorkerMobility, DimCountingPoint         │
├─────────────────────────────────────────────────────────┤
│  Fase 3   │  Feitentabellen                              │
│           │  FactMeteo, FactBlueBike,                    │
│           │  FactWorkerMobility, FactDepartement,        │
│           │  FactStaffCommute, FactCountings             │
└─────────────────────────────────────────────────────────┘
```

Elke fase volgt hetzelfde patroon: **Bouwen → Valideren → Laden**. Als de validatie faalt, stopt de pipeline en wordt er niets geladen.

### Afhankelijkheidsketen

De meeste ETL-functies doen tijdens het bouwen van een DataFrame een `getData()`-aanroep op de live database. Ze verwachten dat bepaalde tabellen al geladen zijn.

```text
DimLocation ─────────────────── geen afhankelijkheden
    │
    ├──► DimBlueBikeStation      getData() op DimLocation (LocationKey via postcode)
    │         │
    │         └──► DimStation    getData() op DimLocation + DimBlueBikeStation
    │
    ├──► DimWeatherStation       getData() op DimLocation
    ├──► DimWorkerMobility       getData() op DimLocation
    └──► DimCountingPoint        getData() op DimLocation

DimDate ─────────────────────── geen afhankelijkheden
    └──► FactStaffCommute        getData() op DimDate (DateKey)

DimDepartement ──────────────── geen afhankelijkheden
    └──► FactDepartement         getData() op DimDepartement (DepartementKey)

DimStaff ────────────────────── geen afhankelijkheden
    └──► FactStaffCommute        getData() op DimStaff (StaffKey)

DimTransportType ────────────── geen afhankelijkheden
    └──► FactWorkerMobility      getData() op DimTransportType (CO2PerKM)

DimBlueBikeStation + DimStation └──► FactBlueBike (beide nodig)

DimWorkerMobility ───────────── geladen in fase 2b
    └──► FactWorkerMobility      getData() op DimWorkerMobility

DimCountingPoint ────────────── geladen in fase 2b
    └──► FactCountings           getData() op DimCountingPoint
```

### Intern mechanisme per blok

Elke fase gebruikt de hulpfunctie `_load_block()` uit `initiator.py`:

```python
def _load_block(engine, candidates, table_names, block_label) -> bool:
    report = validate_subset(candidates, table_names)
    print_report(report)

    if not report.all_passed:
        print(f"Validatie gefaald in {block_label} — pipeline gestopt.")
        return False

    for table_name in table_names:
        df = candidates.get(table_name)
        kwargs = {"if_exists": "replace"} if table_name == "DimWeatherStation" else {}
        if df is not None and not df.empty:
            loadIN(engine, df=df, table=table_name, **kwargs)
        else:
            print(f"  Overgeslagen: {table_name} is leeg — niets te laden.")

    return True
```

`DimWeatherStation` is de enige tabel met `if_exists='replace'`: het is een volledige snapshot die bij elke run vervangen wordt. Alle andere tabellen gebruiken `if_exists='append'`. Lege DataFrames worden stilzwijgend overgeslagen — dit is geen fout.

---

## Fase 1 — Basislaag

Tabellen: `DimTime`, `DimDate`, `DimLocation`, `DimTransportType`, `DimDepartement`, `DimStaff`, `DimStudent`

Geen van deze functies doet een `getData()`-aanroep. Ze halen hun data uitsluitend op uit externe bronnen: Python-logica, vaste bestanden of externe API's.

| Tabel | ETL-functie | Bron | Opmerkingen |
| --- | --- | --- | --- |
| `DimTime` | `dimTime()` | Python-logica | 1440 rijen, éénmalig, verandert nooit |
| `DimDate` | `CreateDimDate()` | Nager.at API + OpenHolidaysAPI | 6209 rijen (2010–2026), feestdagen en schoolvakanties |
| `DimLocation` | `dimLocation()` | Excel (postcodes) | 2764 rijen, meest kritische basistabel van de pipeline |
| `DimTransportType` | `fillTransportType()` | CSV | 8 rijen, CO2-uitstoot per km per transportmiddel |
| `DimDepartement` | `dimDepartement()` | Excel (via e-mail) | Nodig in fase 3 voor `FactDepartement` |
| `DimStaff` | `fillDimStaff()` | CSV | Mag leeg zijn; nodig in fase 3 voor `FactStaffCommute` |
| `DimStudent` | `dimStudent()` | CSV (mobiliteitsbevraging) | Studenten pendeldata |

---

## Fase 2a — DimBlueBikeStation

`dimBlueBikeStation()` haalt alle actieve Blue Bike-stations op via de Blue-bike JSON API. Nieuwe stations (nog niet in de DB) worden gefilterd en krijgen een `LocationKey` via postcode-opzoeking in `DimLocation` (Geopunt Vlaanderen API of Nominatim). Een lege DataFrame is geldig — er zijn dan geen nieuwe stations.

Deze tabel heeft een eigen fase omdat `DimStation` (fase 2b) intern `getData()` doet op `DimBlueBikeStation` voor de afstandsberekening.

---

## Fase 2b — DB-afhankelijke dimensies

Tabellen: `DimWeatherStation`, `DimStation`, `DimWorkerMobility`, `DimCountingPoint`

Alle vier doen ze een `getData()`-aanroep op `DimLocation` (en deels op `DimBlueBikeStation`) om hun `LocationKey` te bepalen.

| Tabel | ETL-functie | Bron | Opmerkingen |
| --- | --- | --- | --- |
| `DimWeatherStation` | `download_aws_stations()` | VMM CSV-API | Snapshot → `replace`. Fallback: LLM voor postcode als Geopunt faalt |
| `DimStation` | `dimStation()` | iRail CSV | Enkel stations binnen straal van een Blue Bike-station; dubbels verwijderd |
| `DimWorkerMobility` | `load_and_preprocess_survey()` | CSV (bevraging) | Coördinaten → postcode → LocationKey; reiswaarden herschaald |
| `DimCountingPoint` | `fillDimCountingPoint()` | Telraam API | Incrementeel; mag leeg zijn |

---

## Fase 3 — Feitentabellen

Tabellen: `FactMeteo`, `FactBlueBike`, `FactWorkerMobility`, `FactDepartement`, `FactStaffCommute`, `FactCountings`

Alle zes bouwen op dimensies die nu volledig in de database staan.

| Tabel | ETL-functie | Wat het doet |
| --- | --- | --- |
| `FactMeteo` | `download_weather_for_date()` | Weermetingen van gisteren via VMM-API. Geeft `None` bij lege respons (geen blokkerende fout) |
| `FactBlueBike` | `factBlueBike()` | Actuele beschikbaarheid Blue Bike + NMBS-koppeling. DateKey + TimeKey op basis van huidig moment |
| `FactWorkerMobility` | `factWorkerMobility()` | CO2-emissie = reisafstand × CO2PerKM. Volledig berekend op basis van DimWorkerMobility + DimTransportType |
| `FactDepartement` | `factDepartement()` | Aantal medewerkers per departement per maand. DateKey = JAAR×10000 + MAAND×100 + 01 |
| `FactStaffCommute` | `fillFactStaffCommute()` | Dagkolommen (dag 1–31) uit fietsvergoeding CSV → rijen per dag. Nullen en onbekende personeelsleden gefilterd |
| `FactCountings` | `fillFactCountings()` | Dagelijkse fietstellingen per telpaal via Telraam API. Incrementeel; mag leeg zijn |

---

## Standalone fillers

Naast de hoofdpipeline zijn er losse scripts die één specifieke tabel bijwerken zonder de volledige pipeline te draaien:

| Script | Tabel(len) | Wanneer te gebruiken |
| --- | --- | --- |
| `factWeather.py` | `FactMeteo` | Weerdata voor een specifieke datum opnieuw laden |
| `fillerBluebikeStation.py` | `FactBlueBike` | Blue Bike-beschikbaarheid handmatig bijwerken |
| `fillerCountingPoints.py` | `DimCountingPoint` + `FactCountings` | Telpalen en hun tellingen incrementeel bijwerken |
| `fillerTrain.py` | `stg_FactTrainArrival` → `FactTrainArrival` | Treindata inladen via staging (2-staps: fetch → promote) |
| `fillerVoorAanpassingen.py` | `FactMeteo` | Identiek aan `factWeather.py`; gebruikt bij handmatige aanpassingen |

Deze scripts voeren dezelfde validatie uit als de hoofdpipeline via `validate_subset()`.

> **Let op:** `fillerTrain.py`, `factWeather.py` en `fillerVoorAanpassingen.py` worden momenteel niet gedekt door de geautomatiseerde validator in de hoofdpipeline.

---

## Validatie

`validator.py` valideert elk DataFrame **vóór** het naar de database wordt geschreven. Als de validatie faalt, stopt de pipeline en wordt er niets geladen.

### Rapportagestructuur

```python
@dataclass
class TableReport:
    table: str
    passed: bool
    errors: list[str]
    row_count: int

@dataclass
class PipelineReport:
    tables: list[TableReport]

    @property
    def all_passed(self) -> bool:
        return all(t.passed for t in self.tables)
```

### Herbruikbare checkfuncties

| Functie | Wat het controleert |
| --- | --- |
| `check_not_empty(df, table)` | DataFrame is niet `None` en niet leeg |
| `check_columns(df, expected, table)` | Alle verwachte kolommen zijn aanwezig |
| `check_no_nulls(df, cols, table)` | Opgegeven kolommen bevatten geen NULL-waarden |
| `check_no_duplicates(df, key_cols, table)` | Geen dubbele rijen op samengestelde sleutel |
| `check_unique_values(df, col, table)` | Enkelvoudige kolom bevat alleen unieke waarden |
| `check_no_negatives(df, cols, table)` | Numerieke kolommen bevatten geen negatieve waarden |
| `check_exact_row_count(df, n, table)` | DataFrame heeft exact het verwachte aantal rijen |
| `check_datekey_format(df, col, table)` | Integer-kolom bevat geldige YYYYMMDD-datums |

### Aanroepvarianten

- `validate_all(candidates)` — valideert alle tabellen in de dictionary
- `validate_subset(candidates, table_names)` — valideert enkel de opgegeven tabellen (gebruikt door `_load_block()`)

### Uitvoerformaat

```text
── Validatierapport ──────────────────────────────────────────────
  [ OK  ] DimTime                   (1440 rijen)
  [ OK  ] DimDate                   (6209 rijen)
  [ FOUT] DimLocation               (0 rijen)
           ! DimLocation: DataFrame is leeg of None
── Resultaat: GEFAALD — niets geladen ──────────────────────────
```

---

## DDL-constraints als laatste vangnet

Zelfs als de Python-validatie iets mist, weigert het DDL-schema foute data op het moment van schrijven.

| Constraint-type | Wat het afdwingt | Waar toegepast |
| --- | --- | --- |
| `CHECK CONSTRAINT` | Geen negatieve waarden in meetkolommen en sleutels | Alle 16 tabellen + staging |
| `PRIMARY KEY` | Geen dubbele rijen op de primaire sleutel | Alle tabellen |
| `UNIQUE` | Geen dubbele waarden op specifieke kolommen | `DimLocation`, `DimStation` (URI), `DimWorkerMobility` (ResponseID), `DimWeatherStation` (Lat/Long) |
| `FOREIGN KEY` | Elke FK-waarde moet bestaan in de dimensie | Alle feitentabellen → dimensies; dimensies met `LocationKey` → `DimLocation` |
| `NOT NULL` | Verplichte velden | `DimStation`, `DimBlueBikeStation`, `FactBlueBike` |

Python valideert **vóór** de load (snelle feedback, geen gedeeltelijke schrijfacties). DDL vangt fouten op **tijdens** de load (absolute last line of defense).

---

## Validatiesamenvatting per tabel

| Tabel | Leeg OK | Kolomcheck | NULL-check op | Duplicaatcheck op | Negatiefcheck | DateKey-formaat | Extra |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `DimTime` | Nee | ✓ | TimeKey, Hour, Minute | TimeKey | ✓ | — | Exact 1440 rijen |
| `DimDate` | Nee | ✓ (28 kol) | DateKey, Year, Month, DayOfMonth | DateKey | ✓ | DateKey | Exact 6209 rijen |
| `DimLocation` | Nee | ✓ | Alle 4 kolommen | (PostalCode, Municipality, ...) | — | — | Exact 2764 rijen |
| `DimTransportType` | Nee | ✓ | VehicleType | VehicleType (unique) | CO2PerKM | — | Exact 8 rijen |
| `DimDepartement` | Nee | ✓ | Year, Month, DepartementName | (Year, Month, DepartementName) | Year, Month | — | — |
| `DimStaff` | **Ja** | ✓ | StaffID | StaffID (unique) | DepartementKey | — | — |
| `DimStudent` | **Ja** | ✓ | — | — | — | — | — |
| `DimBlueBikeStation` | **Ja** | ✓ | BlueBikeStationKey, LocationKey, Lat, Long | BlueBikeStationKey | ✓ | — | — |
| `DimStation` | **Ja** | ✓ | URI, StationName, Latitude, Longitude | URI (unique) | — | — | — |
| `DimWeatherStation` | Nee | ✓ | WeatherStationID, Lat, Long, SnapshotDate | WeatherStationID (unique) | LocationKey | — | — |
| `DimWorkerMobility` | Nee | ✓ (14 kol) | ResponseID, RecordDate | ResponseID (unique) | Reiswaarden | RecordDate | — |
| `DimCountingPoint` | **Ja** | ✓ (14 kol) | CountingPointID, LocationKey | CountingPointID | ✓ | — | — |
| `FactMeteo` | **Ja** | ✓ (20 kol) | WeatherStationKey, DateKey | (WeatherStationKey, DateKey) | 9 meetkol. | DateKey | Niet geblokkeerd bij None |
| `FactBlueBike` | Nee | ✓ | BlueBikeStationKey, DateKey, TimeKey | (BlueBikeStationKey, DateKey, TimeKey) | ✓ | DateKey | — |
| `FactWorkerMobility` | Nee | ✓ | WorkerID, DateKey, TransportKey | — | TotalEmission | — | — |
| `FactDepartement` | Nee | ✓ | DateKey, DepartementKey | (DateKey, DepartementKey) | ✓ | DateKey | — |
| `FactStaffCommute` | Nee | ✓ | StaffKey, DateKey | — | DistanceKM | DateKey | — |
| `FactCountings` | **Ja** | ✓ | CountingPointID, DateKey | (CountingPointID, DateKey) | Telwaarden | DateKey | — |
| `FactTrainArrival` | Nee | ✓ | StationKey, DateKey, StartTime, EndTime | (StationKey, DateKey, StartTime) | ✓ | DateKey | StartTime < EndTime |

---

## Bekende beperkingen

### Standalone fillers en de centrale validator

### Standalone fillers en de validator

`fillerTrain.py`, `factWeather.py` en `fillerVoorAanpassingen.py` draaien buiten de hoofdpipeline. Ze roepen `validate_subset()` aan voor de tabellen die ze laden, maar worden niet automatisch gedekt door de gecentraliseerde validatierapportage in `initiator.py`.
