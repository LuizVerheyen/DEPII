# Testdocumentatie – Data Engineering Project

## Inhoudsopgave

1. [Overzicht teststructuur](#1-overzicht-teststructuur)
2. [Vereisten en configuratie](#2-vereisten-en-configuratie)
3. [Tests uitvoeren](#3-tests-uitvoeren)
4. [Leerkrachten-tests (integratietests)](#4-leerkrachten-tests-integratietests)
   - [test_01 – DimDate](#test_01--dimdate)
   - [test_02 – DimTime](#test_02--dimtime)
   - [test_03 – DimWeatherStation](#test_03--dimweatherstation)
   - [test_04 – FactMeteo](#test_04--factmeteo)
   - [test_05 – DimCountingPoint](#test_05--dimcountingpoint)
   - [test_06 – FactCountings](#test_06--factcountings)
   - [test_07 – DimStation](#test_07--dimstation)
   - [test_08 – DimDepartement](#test_08--dimdepartement)
   - [test_09 – DimStaff](#test_09--dimstaff)
   - [test_10 – FactDepartement](#test_10--factdepartement)
   - [test_11 – FactStaffCommute](#test_11--factstaffcommute)
   - [test_12 – DimTransportType](#test_12--dimtransporttype)
   - [test_15 – DimBlueBikeStation](#test_15--dimbluebikestation)
   - [test_16 – FactBlueBike](#test_16--factbluebike)
5. [Unit-tests](#5-unit-tests)
   - [Dimensies](#dimensies)
   - [Feittabellen](#feittabellen)
6. [SQL-controlevragen](#6-sql-controlevragen)
7. [Testresultaten](#7-testresultaten)

---

## 1. Overzicht teststructuur

```text
tests/
├── TestDocumentatie.md               ← dit bestand
├── SqlTestsLeerkrachten/             ← integratietests tegen de live DWH-database
│   ├── conftest.py                   ← database-fixture en hulpfuncties
│   ├── validation_utils.py           ← herbruikbare checkfabriek
│   ├── test_01_dim_date.py
│   ├── test_02_dim_time.py
│   ├── test_03_weatherstations.py
│   ├── test_04_factmeteo.py
│   ├── test_05_dimtelpalen.py
│   ├── test_06_facttellingen.py
│   ├── test_07_dimtrainstations.py
│   ├── test_08_dimdepartment.py
│   ├── test_09_dimemployee.py
│   ├── test_10_factdepartment_headcount.py
│   ├── test_11_fact_bike_kilometers_employees.py
│   ├── test_12_dimtransportmode.py
│   ├── test_15_blue_bike_locaties.py
│   ├── test_16_blue_bike_countings.py
│   └── Testen_Leerkrachten_Output.txt   ← geslaagde testrun-output
├── unitTests/                        ← unit-tests op transformatiefuncties
│   ├── conftest.py                   ← logging-setup voor unit-tests
│   ├── test_dim_date.py
│   ├── test_dim_time.py
│   ├── test_dim_location.py
│   ├── test_dim_staff.py
│   ├── test_dim_transport_type.py
│   ├── test_dim_bluebike_station.py
│   ├── test_dim_counting_point.py
│   ├── test_dim_departement.py
│   ├── test_dim_station.py
│   ├── test_dim_weather_station.py
│   ├── test_dim_worker_mobility.py
│   ├── test_dim_student.py
│   ├── test_fact_bluebike.py
│   ├── test_fact_countings.py
│   ├── test_fact_departement.py
│   ├── test_fact_meteo.py
│   ├── test_fact_staff_commute.py
│   ├── test_fact_train_arrival.py
│   ├── test_fact_worker_mobility.py
│   └── test_fact_student_mobility.py
└── sqlTests/
    └── queries_ter_controle_van_DWH.sql  ← manuele SQL-verificaties
```

Er zijn twee soorten geautomatiseerde tests:

| Type | Map | Vereist een live DB? | Doel |
| --- | --- | --- | --- |
| **Integratietests** | `SqlTestsLeerkrachten/` | Ja (SQL Server DEPI) | Valideer data in het volledig gevulde DWH |
| **Unit-tests** | `unitTests/` | Nee | Valideer de transformatielogica per functie |

---

## 2. Vereisten en configuratie

### Python-pakketten

```
pytest
pyodbc
python-dotenv
pandas
```

### Omgevingsvariabelen (`.env`)

De integratietests lezen hun databaseverbinding uit `.env` in de projectroot:

```env
DB_SERVER=127.0.0.1,2222
DB_NAME=DEPI
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_USER=sa
databasePWD=<jouw wachtwoord>
```

---

## 3. Tests uitvoeren

### Alle integratietests (leerkrachten)

```bash
python -m pytest tests/SqlTestsLeerkrachten -v -s --cache-clear
```

### Alle unit-tests

```bash
python -m pytest tests/unitTests -v
```

### Alle tests tegelijk

```bash
python -m pytest tests/ -v
```

Na afloop van de integratietests wordt automatisch een **validatierapport per tabel** afgedrukt, gevolgd door een algemene samenvatting (zie [Testresultaten](#7-testresultaten)).

---

## 4. Leerkrachten-tests (integratietests)

Deze tests verbinden rechtstreeks met de SQL Server-database `DEPI` en voeren SQL-queries uit om de inhoud van elke tabel te valideren. Ze gebruiken de helperfuncties uit `conftest.py`:

- `run_check` – voert een SQL-query uit en vergelijkt het resultaat met een operator (`==`, `>`, `!=`, …)
- `run_custom_check` – vergelijkt de queryuitkomst exact met een verwachte waarde
- `run_range_check` – valideert dat een waarde binnen een [min, max]-bereik valt
- `run_tolerance_check` – valideert met een zwevende-komma-tolerantie (standaard ±0,1)

---

### test_01 – DimDate

**Bestand:** `testsLeerkrachten/test_01_dim_date.py`

Valideert de datumsdimensie die de periode 01/01/2020 t.e.m. 31/12/2025 dekt.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Exacte rijtelling | 2192 |
| Geen NULL in DateKey | Geen lege sleutelwaarden | 0 NULL's |
| Unieke waarden in DateKey | Geen duplicaten | 0 duplicaten |
| Datumattributen (×6) | DayOfMonth, Month, Year, DayNameEN, DayNameNL, MonthNameEN, MonthNameNL correct voor 6 specifieke datums | 1 overeenkomst per datum |

Gecontroleerde datums: `20200803`, `20210406`, `20220525`, `20230622`, `20240712`, `20250920`.

---

### test_02 – DimTime

**Bestand:** `testsLeerkrachten/test_02_dim_time.py`

Valideert de tijdsdimensie (één rij per minuut van de dag).

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | 60 min × 24 uur | 1440 |
| Geen NULL in TimeKey | Geen lege sleutelwaarden | 0 NULL's |
| Unieke waarden in TimeKey | Geen duplicaten | 0 duplicaten |
| Tijdattributen (×7) | Hour, Minute, AMPM, Hour12 correct voor 7 specifieke tijdstippen | 1 overeenkomst per tijdstip |

Gecontroleerde tijdstippen (als integer TimeKey): `12`, `157`, `324`, `641`, `1110`, `1503`, `1637`.

---

### test_03 – DimWeatherStation

**Bestand:** `testsLeerkrachten/test_03_weatherstations.py`

Valideert de weerstationsdimensie.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Exacte telling | 14 |
| Geen NULL in Name | Geen lege namen | 0 NULL's |
| Geen lege waarden in Name | Geen lege strings | 0 lege waarden |
| Unieke waarden in Latitude | Elke breedtegraad uniek | 0 duplicaten |
| Unieke waarden in Longitude | Elke lengtegraad uniek | 0 duplicaten |

---

### test_04 – FactMeteo

**Bestand:** `testsLeerkrachten/test_04_factmeteo.py`

Valideert de meteorologische feitentabel.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Geen NULL in DateKey, WeatherStationKey | Geen lege samengestelde sleutels | 0 NULL's |
| Unieke sleutel op DateKey, WeatherStationKey | Geen dubbele combinaties | 0 duplicaten |
| Metingstelling per station (×14) | Correct aantal dagmetingen per station | 2192 (de meeste), 300 (DE HAAN) |
| Statistieken BEITEM | Max/min gemiddelde temp, max/min van min/max temp, gemiddelde neerslag | Met tolerantie ±0,1 |
| Statistieken ZEEBRUGGE | Zelfde reeks statistieken | Met tolerantie ±0,1 |

Voorbeeldwaarden BEITEM: max gemiddelde temp = 28,60 °C, min van min temp = −8,38 °C.
Voorbeeldwaarden ZEEBRUGGE: max gemiddelde temp = 28,55 °C, min van min temp = −6,01 °C.

---

### test_05 – DimCountingPoint

**Bestand:** `testsLeerkrachten/test_05_dimtelpalen.py`

Valideert de fietstelpalen-dimensie.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Exacte telling | 356 |
| Geen NULL in CountingPointName | Geen lege namen | 0 NULL's |
| Geen lege waarden in CountingPointName | Geen lege strings | 0 lege waarden |
| Unieke waarden in CountingPointID | Geen duplicaten | 0 duplicaten |

---

### test_06 – FactCountings

**Bestand:** `testsLeerkrachten/test_06_facttellingen.py`

Valideert de fietstelpaal-tellingenfeitentabel.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (472 405 bij laatste run) |
| Geen NULL in DateKey, CountingPointID | Geen lege samengestelde sleutels | 0 NULL's |
| Geen lege waarden in DateKey, CountingPointID | Geen lege strings | 0 lege waarden |
| Unieke sleutel op DateKey, CountingPointID | Geen dubbele combinaties | 0 duplicaten |
| Gemiddeld dagaantal fietsers (×5 locaties) | Gemiddeld binnen verwacht bereik | Zie tabel hieronder |
| Totaaltelling (×4 telpalen) 2022–2023 | Exact totaal voor de volledige periode | Zie tabel hieronder |

**Bereikcontroles (gemiddeld dagaantal):**

| Locatie | Min | Max |
|---------|-----|-----|
| Menenstraat (Zuid) | 46 | 1047 |
| Desguinlei (Zuid) | 2 | 56 517 |
| Langerbruggestraat | 13 | 1234 |
| Fietsen Door De Bomen H | 0 | 16 682 |
| Terminal Brussels Airport | 26 | 324 |

**Totaaltellingen 2022–2023:**

| Telpaal | Totaal |
|---------|--------|
| Fintele | 134 070 |
| Jaagpad Bovenschelde | 359 952 |
| Dudzeelse Steenweg (West) | 210 686 |
| Lierseweg brug (Oost) | 494 815 |

---

### test_07 – DimStation

**Bestand:** `testsLeerkrachten/test_07_dimtrainstations.py`

Valideert de treinstationnsdimensie (joined met DimLocation).

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Exacte telling | 125 |
| Geen NULL in StationName | Geen lege namen | 0 NULL's |
| Geen lege waarden in StationName | Geen lege strings | 0 lege waarden |
| Unieke sleutel op Latitude, Longitude | Geen dubbele coördinaten | 0 duplicaten |
| Unieke waarden in StationName | Geen dubbele namen | 0 duplicaten |
| Aantal stations per provincie (×7) | Correcte verdeling | Zie tabel hieronder |
| Aantal stations per gemeente (×6) | Correcte telling per gemeente | Zie tabel hieronder |

**Stations per provincie:**

| Provincie | Verwacht | Tolerantie |
|-----------|----------|------------|
| Antwerpen | 22 | ±2 |
| West-Vlaanderen | 18 | ±2 |
| Oost-Vlaanderen | 36 | ±2 |
| Vlaams-Brabant | 29 | ±2 |
| Limburg | 11 | ±2 |
| Namen | 1 | ±2 |
| Henegouwen | 1 | ±2 |

**Stations per gemeente:**

| Gemeente | Verwacht |
|----------|----------|
| Antwerpen | 5 |
| Ieper | 1 |
| Lokeren | 1 |
| Lanaken | 0 |
| Zeebrugge | 2 |
| Testelt | 1 |

---

### test_08 – DimDepartement

**Bestand:** `testsLeerkrachten/test_08_dimdepartment.py`

Valideert de afdelingsdimensie.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Exacte telling | 40 |
| Geen NULL in DepartementName | Geen lege namen | 0 NULL's |
| Geen lege waarden in DepartementName | Geen lege strings | 0 lege waarden |
| Unieke waarden in DepartementName | Geen dubbele namen | 0 duplicaten |

---

### test_09 – DimStaff

**Bestand:** `testsLeerkrachten/test_09_dimemployee.py`

Valideert de personeelsdimensie (medewerkers met fietsvergoeding).

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één medewerker | > 1 (462 bij laatste run) |
| Geen NULL in StaffKey, StaffID, Campus, DepartementKey | Geen lege kernkolommen | 0 NULL's |
| Geen lege waarden in Campus | Geen lege campuswaarden | 0 lege waarden |
| Unieke waarden in StaffKey | Geen dubbele surrogatsleutels | 0 duplicaten |
| Unieke waarden in StaffID | Geen dubbele bedrijfs-ID's | 0 duplicaten |
| Geen negatieve sleutels | StaffKey en DepartementKey ≥ 0 | 0 negatieve waarden |

---

### test_10 – FactDepartement

**Bestand:** `testsLeerkrachten/test_10_factdepartment_headcount.py`

Valideert de maandelijkse personeelsbezetting per afdeling.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (1426 bij laatste run) |
| Geen NULL in DateKey, DepartementKey | Geen lege samengestelde sleutels | 0 NULL's |
| Geen lege waarden in DateKey, DepartementKey | Geen lege strings | 0 lege waarden |
| Unieke sleutel op DateKey, DepartementKey | Geen dubbele combinaties | 0 duplicaten |
| Records in 2024 | Aantal snapshots voor het volledige jaar | 477 |
| Som werknemers januari 2024 | Totaal personeelsleden op 01/01/2024 | 2384 |
| Som werknemers april 2025 | Totaal personeelsleden op 01/04/2025 | 2300 |

---

### test_11 – FactStaffCommute

**Bestand:** `testsLeerkrachten/test_11_fact_bike_kilometers_employees.py`

Valideert de fietsvergoedingsfeitentabel (dagelijkse pendeldistanties van personeel).

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (89 319 bij laatste run) |
| Geen NULL in DateKey, StaffKey | Geen lege samengestelde sleutels | 0 NULL's |
| Geen lege waarden in DateKey, StaffKey | Geen lege strings | 0 lege waarden |
| Unieke sleutel op StaffCommuteKey | Geen dubbele primaire sleutels | 0 duplicaten |
| Totale kilometers (×6 datums) | Exact totaal km per dag (tolerantie ±0,1) | Zie tabel hieronder |

**Kilometer-totalen per dag:**

| Datum | Verwacht totaal (km) |
|-------|----------------------|
| 20240108 | 2739,00 |
| 20240304 | 2789,00 |
| 20240607 | 2159,00 |
| 20250219 | 5224,10 |
| 20250510 | 11,00 |
| 20251112 | 1826,80 |

---

### test_12 – DimTransportType

**Bestand:** `testsLeerkrachten/test_12_dimtransportmode.py`

Valideert de transportwijzendimensie.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (8 bij laatste run) |
| Geen NULL in VehicleType | Geen lege vervoerstypen | 0 NULL's |
| Unieke waarden in VehicleType | Geen dubbele namen | 0 duplicaten |
| CO2PerKM-waarden (×8 modi) | Correct uitstootgetal per modus | Zie tabel hieronder |

**CO2-uitstoot per vervoersmodus:**

| Vervoersmodus | CO2PerKM (kg/km) |
|---------------|-----------------|
| Trein | 0,02 |
| Bus | 0,03 |
| Auto | 0,15 |
| Vliegtuig-700 | 0,20 |
| Vliegtuig+700 | 0,30 |
| Vliegtuig+2500 | 0,40 |
| Fiets | 0,00 |
| Boot | 0,00 |

---

### test_15 – DimBlueBikeStation

**Bestand:** `testsLeerkrachten/test_15_blue_bike_locaties.py`

Valideert de Blue Bike-stationsdimensie (joined met DimLocation).

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (253 bij laatste run) |
| Geen NULL in LocationName | Geen lege namen | 0 NULL's |
| Geen lege waarden in LocationName | Geen lege strings | 0 lege waarden |
| Unieke sleutel op Latitude, Longitude | Geen dubbele coördinaten | 0 duplicaten |
| Unieke waarden in LocationName | Geen dubbele locatienamen | 0 duplicaten |
| Stations per provincie (×7) | Correcte verdeling | Zie tabel hieronder |
| Stations per postcode (×4) | Correcte telling per postcode | Zie tabel hieronder |
| Locaties met "station" in naam | Telling | 131 |

**Blue Bike-stations per provincie:**

| Provincie | Verwacht | Tolerantie |
|-----------|----------|------------|
| Antwerpen | 40 | ±2 |
| Oost-Vlaanderen | 87 | ±2 |
| West-Vlaanderen | 21 | ±2 |
| Limburg | 21 | ±2 |
| Vlaams-Brabant | 74 | ±2 |
| Luik | 1 | ±2 |
| Henegouwen | 1 | ±2 |

**Blue Bike-stations per postcode:**

| Postcode | Verwacht |
|----------|----------|
| 9000 | 3 |
| 9051 | 1 |
| 9800 | 2 |
| 8500 | 2 |

---

### test_16 – FactBlueBike

**Bestand:** `testsLeerkrachten/test_16_blue_bike_countings.py`

Valideert de Blue Bike-beschikbaarheidsfeitentabel.

| Test | Beschrijving | Verwacht |
|------|-------------|----------|
| Aantal rijen | Minimaal één rij | > 0 (275 859 bij laatste run) |
| Geen NULL in DateKey, TimeKey, BlueBikeStationKey | Geen lege samengestelde sleutels | 0 NULL's |
| Geen lege waarden in DateKey, TimeKey, BlueBikeStationKey | Geen lege strings | 0 lege waarden |
| Unieke sleutel op DateKey, TimeKey, BlueBikeStationKey | Geen dubbele combinaties | 0 duplicaten |
| Gemiddeld beschikbare fietsen (×4 locaties) | Gemiddelde binnen verwacht bereik | Zie tabel hieronder |

**Gemiddeld beschikbare fietsen per locatie:**

| Locatie | Min | Max |
|---------|-----|-----|
| Oostende | 60 | 80 |
| Deinze station | 80 | 115 |
| Ieper | 5 | 10 |
| Machelen | 2 | 15 |

---

## 5. Unit-tests

Unit-tests valideren de Python-transformatiefuncties in isolatie, zonder databaseverbinding. Ze werken met in-memory pandas DataFrames en mocks.

### Dimensies

#### DimDate – `test_dim_date.py`
**Functie:** `CreateDimDate()`

| Test | Beschrijving |
|------|-------------|
| Structuur en bereik | 28 kolommen aanwezig, 6209 rijen, DateKey-bereik 20100101–20261231, uniekheidscontrole |
| Bekende datums | 2 specifieke datums gecontroleerd op correcte dag/maand/kwartaalnamen |
| Feest- en schoolvakantiemarkeringen | Nieuwjaarsmarkering als feestdag, zomervakantie als schoolvakantie, werkdaglogica |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimTime – `test_dim_time.py`
**Functie:** `dimTime()`

| Test | Beschrijving |
|------|-------------|
| Structuur en bereik | 6 kolommen, 1440 rijen, TimeKey uniek (0–2359) |
| Bekende tijdstippen | 4 tijdstippen (middernacht, 08:30, middag, 23:59) gecontroleerd op hour/minute/AMPM/Hour12 |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimLocation – `test_dim_location.py`
**Functie:** `dimLocation()`

| Test | Beschrijving |
|------|-------------|
| Structuur en sleutels | 4 kolommen, 2764 rijen, geen duplicaten op de natuurlijke sleutel |
| Bekende rijen | 3 locaties (Gent, Brugge, Antwerpen) gecontroleerd op postcode/gemeente/provincie |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimStaff – `test_dim_staff.py`
**Functie:** `fillDimStaff()`

| Test | Beschrijving |
|------|-------------|
| Afdelingstoewijzing en ontdubbeling | 3 verwachte kolommen, verwijdert dubbele medewerkers, koppelt StaffID correct aan DepartementKey |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimTransportType – `test_dim_transport_type.py`
**Functie:** `fillTransportType()`

| Test | Beschrijving |
|------|-------------|
| Structuur en sleutels | 2 kolommen, 8 rijen, VehicleType uniek |
| Bekende waarden | 8 vervoersmodi gecontroleerd op correcte CO2PerKM-waarden |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimBlueBikeStation – `test_dim_bluebike_station.py`
**Functie:** `dimBlueBikeStation()`

| Test | Beschrijving |
|------|-------------|
| Enkel nieuwe stations | Filtert op stations die nog niet in de database staan, koppelt LocationKey |
| Leeg resultaat | Geeft lege DataFrame terug wanneer alle stations al bestaan |

#### DimCountingPoint – `test_dim_counting_point.py`
**Functie:** `fillDimCountingPoint()`

| Test | Beschrijving |
|------|-------------|
| Transformatie nieuwe rijen | 14 kolommen, transformeert telpaaldata met LocationKey-koppeling |
| Leeg resultaat | Geeft lege DataFrame bij geen nieuwe rijen |

#### DimDepartement – `test_dim_departement.py`
**Functie:** `dimDepartement()`

| Test | Beschrijving |
|------|-------------|
| Structuur en waarden | 3 kolommen (DepartementName, StartDate, EndDate), 2 afdelingen |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimStation – `test_dim_station.py`
**Functie:** `dimStation()`

| Test | Beschrijving |
|------|-------------|
| Nabijheidsfilter | Behoudt enkel stations binnen afstandsdrempel van Blue Bike-locaties, valideert structuur |
| Ontdubbeling | Verwijdert dubbele rijen wanneer meerdere Blue Bike-stations bij hetzelfde treinstation liggen |

#### DimWeatherStation – `test_dim_weather_station.py`
**Functie:** `download_aws_stations()`

| Test | Beschrijving |
|------|-------------|
| Snapshot-opbouw | 8 kolommen, parst AWS-stations met numerieke hoogte/lat/lon, voegt LocationKey en SnapshotDate toe |
| Foutafhandeling | Geeft `None` terug bij een mislukt HTTP-verzoek |

#### DimWorkerMobility – `test_dim_worker_mobility.py`
**Functie:** `load_and_preprocess_survey()`

| Test | Beschrijving |
|------|-------------|
| Transformatie brondata | 14 kolommen, datumverwerking, afstandseenheidsconversie (cm → km), vervoerstype-mapping |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### DimStudent – `test_dim_student.py`
**Functie:** `fillDimStudent()`

| Test | Beschrijving |
|------|-------------|
| Transformatie brondata | 2 kolommen, verwijdert duplicaten, filtert op studenten die nog niet in de database staan |
| Deterministisch | Identieke output bij herhaalde aanroepen |

---

### Feittabellen

#### FactBlueBike – `test_fact_bluebike.py`
**Functie:** `factBlueBike()`

| Test | Beschrijving |
|------|-------------|
| Feitrijen opbouwen | 10 verwachte kolommen, correct DateKey, TimeKey, stationkoppeling en fietsen in gebruik |
| Stationkoppeling op afstand | `get_linked_station_key` kiest het dichtstbijzijnde station binnen max_distance |

#### FactCountings – `test_fact_countings.py`
**Functie:** `fillFactCountings()`

| Test | Beschrijving |
|------|-------------|
| Tellingtransformatie | 5 kolommen, DateKey afgeleid van datum, richtings- en totaaltellingen behouden |
| Lege dimensie | Geeft lege DataFrame bij lege dimensietabel |

#### FactDepartement – `test_fact_departement.py`
**Functie:** `factDepartement()`

| Test | Beschrijving |
|------|-------------|
| Maandelijkse snapshots | 3 kolommen, bouwt maandelijkse bezettingssnapsshots met correcte DateKey-afleiding |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### FactMeteo – `test_fact_meteo.py`
**Functie:** `download_weather_for_date()`

| Test | Beschrijving |
|------|-------------|
| Brondata-transformatie | 20 weerskolommen, transformeert CSV naar feitstructuur met DateKey en meetwaarden |
| Lege API-respons | Geeft `None` terug bij lege API-respons |

#### FactStaffCommute – `test_fact_staff_commute.py`
**Functie:** `fillFactStaffCommute()`

| Test | Beschrijving |
|------|-------------|
| Feitrijen opbouwen | 4 kolommen, transformeert dagelijkse pendeldata met StaffKey/DateKey/Period/DistanceKM |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### FactTrainArrival – `test_fact_train_arrival.py`
**Functies:** `fetch_and_upsert_staging()` en `promote_stable_to_fact()`

| Test | Beschrijving |
|------|-------------|
| Staging-upsert | Werkt vertragingen bij, voegt nieuwe treinen toe, behoudt oude records |
| Promotie naar feit | Verplaatst enkel stabiele 30-minuut-tijdvensters naar de feitentabel, laat instabiele records in staging |
| Lege staging | Geeft `None` terug wanneer de stagingtabel leeg is |

#### FactWorkerMobility – `test_fact_worker_mobility.py`
**Functie:** `factWorkerMobility()`

| Test | Beschrijving |
|------|-------------|
| CO2-berekening | 4 kolommen, berekent CO2-uitstoot als afstand × CO2PerKM |
| Deterministisch | Identieke output bij herhaalde aanroepen |

#### FactStudentMobility – `test_fact_student_mobility.py`
**Functie:** `fillFactStudentMobility()`

| Test | Beschrijving |
|------|-------------|
| Transformatie brondata | 4 kolommen (StudentKey, DateKey, TransportKey, DistanceKM), records matchen verwachte student/transport-koppeling |
| Deterministisch | Identieke output bij herhaalde aanroepen |

---

## 6. SQL-controlevragen

In `sqlTests/queries_ter_controle_van_DWH.sql` staan manuele SQL-queries om het DWH te verifiëren. Dit zijn geen geautomatiseerde pytest-tests maar controlevragen die handmatig worden uitgevoerd (bijv. in SSMS of Azure Data Studio).

Voorbeelden:

- Aantal records in DimDate na 2016: `SELECT COUNT(*) FROM DimDate WHERE DateKey > 20161230`
- Weerstationsstatistieken voor Zeebrugge (max/min temp, neerslag)
- Blue Bike-stations per provincie
- Telpalen per provincie
- Totaaltelling fietsers 2025 voor telpaal Fintele
- Medewerkers per afdeling en campus
- CO2-uitstoot per vervoersmodus (`DimTransportType` × `FactWorkerMobility`)
- Treinaankomsten gisteren in Kortrijk

---

## 7. Testresultaten

Onderstaande samenvatting is afkomstig uit de meest recente succesvolle run van de integratietests
(zie ook `SqlTestsLeerkrachten/Testen_Leerkrachten_Output.txt`):

```
python -m pytest tests/SqlTestsLeerkrachten -v -s --cache-clear
platform win32 -- Python 3.12.8, pytest-9.0.2
collected 140 items
```

> **140 vs 152:** pytest telt 140 testfuncties (waarvan meerdere geparametriseerd zijn). De `conftest.py` valideert intern elke afzonderlijke check en telt er 152 in totaal. Beide getallen zijn correct — ze meten het op een verschillend niveau.

| Tabel | Geslaagd | Gefaald | Totaal |
|-------|----------|---------|--------|
| DimDate | 9 | 0 | 9 |
| DimTime | 10 | 0 | 10 |
| DimWeatherStation | 5 | 0 | 5 |
| FactMeteo | 30 | 0 | 30 |
| DimCountingPoint | 4 | 0 | 4 |
| FactCountings | 13 | 0 | 13 |
| DimStation (JOIN DimLocation) | 18 | 0 | 18 |
| DimDepartement | 4 | 0 | 4 |
| DimStaff | 6 | 0 | 6 |
| FactDepartement | 7 | 0 | 7 |
| FactStaffCommute | 10 | 0 | 10 |
| DimTransportType | 11 | 0 | 11 |
| DimBlueBikeStation | 17 | 0 | 17 |
| FactBlueBike | 8 | 0 | 8 |
| **Totaal** | **152** | **0** | **152** |

**Resultaat: 140 tests geslaagd in 6,67 seconden.**
