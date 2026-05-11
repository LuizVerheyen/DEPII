# DEPI Web API

REST-API gebouwd bovenop de DEPI Data Warehouse (SQL Server). De API is geschreven in Python met Flask en gebruikt stored procedures voor alle database-queries.

---

## Inhoudsopgave

1. [Overzicht](#overzicht)
2. [Mappenstructuur](#mappenstructuur)
3. [Installatie en configuratie](#installatie-en-configuratie)
4. [API starten](#api-starten)
5. [Endpoints](#endpoints)
   - [Systeem](#systeem)
   - [Telpalen (Counting Points)](#telpalen-counting-points)
   - [Weerstations (Weather Stations)](#weerstations-weather-stations)
   - [Blue Bike-stations](#blue-bike-stations)
6. [Foutafhandeling](#foutafhandeling)
7. [Validatieregels](#validatieregels)
8. [Logging en metrics](#logging-en-metrics)
9. [Stored Procedures](#stored-procedures)
10. [Testen](#testen)
11. [Architectuur](#architectuur)

---

## Overzicht

De Web API biedt een REST-interface over de data in de DEPI Data Warehouse. De API maakt het mogelijk om:

- Fietstellingen op te vragen per telpaal (per periode of specifieke datum)
- Winddata op te vragen per weerstation
- Blue Bike-beschikbaarheid op te vragen per locatie
- De DWH-pipeline asynchroon te starten via een refresh-endpoint
- Operationele statistieken (metrics) te bekijken |

---

## Mappenstructuur

```text
api/
├── __init__.py
├── app.py              # Flask app factory, request-hooks, blueprint-registratie
├── run.py              # Lokale entry-point (python -m api.run)
├── config.py           # Configuratie via omgevingsvariabelen / .env
├── db.py               # Database-laag: get_connection() en call_proc()
├── errors.py           # APIError-klasse + Flask error-handlers
├── validators.py       # Invoer-validatie (datum, periode, integer)
├── logging_setup.py    # Roterende file-logs (webapi.log)
├── metrics.py          # In-memory MetricsStore: count, avg/min/max responstijd
├── openapi.yaml        # OpenAPI 3.0 specificatie (Swagger UI via /api/v1/docs)
├── requirements.txt    # API-specifieke dependencies
├── blueprints/
│   ├── __init__.py
│   ├── health.py       # GET /health
│   ├── counting.py     # /counting-points en totals
│   ├── weather.py      # /weather-stations en wind
│   ├── bluebike.py     # /blue-bike-stations en availability
│   ├── dwh.py          # POST/GET /dwh/refresh
│   ├── metrics_bp.py   # GET/DELETE /metrics
│   ├── extras.py       # /counting-points/top-busiest
│   └── docs.py         # /docs en /openapi.yaml
├── sql/
│   └── stored_procedures.sql   # Stored procedures voor DEPI-database (1x uitvoeren)
└── logs/               # Wordt automatisch aangemaakt bij opstart
```

---

## Installatie en configuratie

### 1. Stored procedures aanmaken

Voer het SQL-script eenmalig uit op de DEPI-database:

```bash
sqlcmd -S 127.0.0.1 -U sa -P "<wachtwoord>" -d DEPI -i api/sql/stored_procedures.sql
```

Dit maakt de volgende stored procedures aan (bestaande versies worden vervangen):

| Stored Procedure                        | Doel                                                        |
| --------------------------------------- | ----------------------------------------------------------- |
| `dbo.sp_Countings_SincePeriodStart`     | Fietstellingen voor een telpaal vanaf start van een periode |
| `dbo.sp_Countings_OnDay`                | Fietstellingen voor een telpaal op een specifieke dag       |
| `dbo.sp_Weather_WindForDay`             | Windgegevens voor een weerstation op een specifieke dag     |
| `dbo.sp_BlueBike_AvailabilityLast7Days` | Min/max beschikbare fietsen per Blue Bike-locatie (7 dagen) |
| `dbo.sp_HealthCheck`                    | DB-bereikbaarheid en tabel-tellingen                        |
| `dbo.sp_List_CountingPoints`            | Alle telpalen oplijsten                                     |
| `dbo.sp_List_WeatherStations`           | Alle weerstations oplijsten                                 |
| `dbo.sp_List_BlueBikeStations`          | Alle Blue Bike-locaties oplijsten                           |
| `dbo.sp_Countings_TopBusiestPoints`     | Top N drukste telpalen op een datum                         |

### 2. Dependencies installeren

De API-specifieke packages staan in `api/requirements.txt`. De root-`requirements.txt` bevat de gedeelde dependencies (`pyodbc`, `python-dotenv`, enz.).

```bash
pip install -r api/requirements.txt
```

### 3. Omgevingsvariabelen (.env)

Maak een `.env`-bestand aan in de projectwortel (of stel de variabelen in via de omgeving). De API hergebruikt dezelfde DB-instellingen als de rest van het project:

```env
# Database (verplicht)
DB_SERVER=127.0.0.1,1433
DB_NAME=DEPI
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_USER=sa
databasePWD=<jouw_wachtwoord>

# API (optioneel, defaults hieronder)
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=false
API_LOG_LEVEL=INFO
API_LOG_DIR=logging/webapi
DWH_REFRESH_TIMEOUT=1800
```

---

## API starten

### Lokaal (ontwikkeling)

```bash
python -m api.run
```

De API is daarna bereikbaar op `http://localhost:5000`.

### Op de Ubuntu VM (productie)

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 'api.app:create_app()'
```

Open eventueel de firewall-poort:

```bash
sudo ufw allow 5000/tcp
```

### Root-endpoint

`GET /` geeft een welkomst-JSON terug met links naar health, metrics en documentatie:

```json
{
  "name": "DEPI Data Warehouse REST API",
  "version": "1.0.0",
  "documentation": "/api/v1/docs",
  "health": "/api/v1/health",
  "metrics": "/api/v1/metrics",
  "server_time": "2025-05-08T10:00:00Z"
}
```

---

## Endpoints

Alle endpoints zitten onder het prefix `/api/v1`. Gebruik voor lokale tests `http://localhost:5000/api/v1/...`.

### Systeem

#### `GET /api/v1/health`

Controleert of de API en de database bereikbaar zijn. Geeft ook het aantal records in de drie hoofddimensie-tabellen terug.

**Response 200 — OK:**

```json
{
  "counts": {
    "blue_bike_stations": 275,
    "counting_points": 362,
    "weather_stations": 14
  },
  "database": "DEPI",
  "server_time_utc": "2026-05-10T19:27:41.836918",
  "status": "ok"
}
```

**Response 503 — DB niet bereikbaar:**

```json
{
  "status": "unavailable",
  "error": "..."
}
```

---

#### `POST /api/v1/dwh/refresh`

Start een volledige DWH-refresh asynchroon in een achtergrond-thread. Er kan maar één refresh tegelijk lopen.

**Response 202 — Gestart:**

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "running",
  "status_url": "/api/v1/dwh/refresh/a1b2c3d4e5f6"
}
```

**Response 409 — Al een refresh actief:**

```json
{
  "error": "Er loopt al een DWH-refresh.",
  "active_job_id": "a1b2c3d4e5f6",
  "status": 409
}
```

---

#### `GET /api/v1/dwh/refresh/<job_id>`

Vraagt de status op van een specifieke refresh-job.

**Response 200:**

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "completed",
  "started_at": "2025-05-08T10:00:00Z",
  "finished_at": "2025-05-08T10:05:00Z"
}
```

Mogelijke `status`-waarden: `running`, `completed`, `failed`.

**Response 404** wanneer het `job_id` onbekend is.

---

#### `GET /api/v1/dwh/refresh`

Geeft een lijst van alle bekende refresh-jobs (in-memory, verdwijnt bij herstart).

```json
{
  "active_job_id": null,
  "count": 2,
  "jobs": [...]
}
```

---

#### `GET /api/v1/metrics`

Geeft per endpoint het aantal aanroepen, het aantal fouten (HTTP 4xx/5xx), en de gemiddelde, minimale en maximale responstijd in milliseconden.

```json
{
  "generated_at": "2025-05-08T10:00:00Z",
  "total_requests": 123,
  "endpoints": {
    "GET counting.list_counting_points": {
      "count": 10,
      "errors": 0,
      "avg_ms": 45.12,
      "max_ms": 120.3,
      "min_ms": 22.05,
      "last_status": 200
    }
  }
}
```

---

#### `DELETE /api/v1/metrics`

Reset alle in-memory metrics. Handig voor een schone demo of eindevaluatie.

```json
{ "status": "reset" }
```

---

#### `GET /api/v1/docs`

Opent de Swagger UI. Alle endpoints zijn interactief uitprobeerbaar.

#### `GET /api/v1/openapi.yaml`

Levert de ruwe OpenAPI 3.0 YAML-specificatie.

---

### Telpalen (Counting Points)

#### `GET /api/v1/counting-points`

Geeft alle telpalen terug gesorteerd op naam.

```json
{
  "count": 42,
  "items": [
    {
      "CountingPointID": 5070,
      "CustomID": "...",
      "CountingPointName": "Gentbrugge brug",
      "Latitude": 51.03,
      "Longitude": 3.74,
      "FirstData": "2021-01-01",
      "Granularity": "hour",
      "Directional": true,
      "DomainName": "Gent"
    }
  ]
}
```

---

#### `GET /api/v1/counting-points/<id>`

Detail van één telpaal op basis van `CountingPointID`.

**Response 404** wanneer de telpaal niet bestaat.

---

#### `GET /api/v1/counting-points/<id>/totals`

Totaal aantal fietsers voor een telpaal. **Geef exact één van de twee query-parameters op:**

| Parameter | Verplicht | Waarden                        | Beschrijving                                   |
| --------- | --------- | ------------------------------ | ---------------------------------------------- |
| `period`  | Nee       | `day`, `week`, `month`, `year` | Totaal vanaf de start van deze periode         |
| `date`    | Nee       | `YYYY-MM-DD`                   | Totaal op een specifieke dag (in het verleden) |

`period`-periodes starten altijd op:

- `day` → vandaag om middernacht
- `week` → de afgelopen maandag (ISO-week)
- `month` → de eerste van deze maand
- `year` → 1 januari van dit jaar

**Voorbeeld — periode:**

```bash
curl "http://localhost:5000/api/v1/counting-points/5070/totals?period=month"
```

```json
{
  "counting_point_id": 5070,
  "period": "month",
  "start_date": "2025-05-01",
  "end_date": "2025-05-08",
  "total_counts": 12500,
  "direction_in": 6300,
  "direction_out": 6200
}
```

**Voorbeeld — specifieke datum:**

```bash
curl "http://localhost:5000/api/v1/counting-points/5070/totals?date=2025-03-01"
```

```json
{
  "counting_point_id": 5070,
  "date": "2025-03-01",
  "total_counts": 850,
  "direction_in": 420,
  "direction_out": 430
}
```

**Foutgevallen:**

- `400` — geen of beide parameters opgegeven
- `400` — `date` is vandaag of in de toekomst
- `400` — ongeldige datumnotatie of ongeldige periode
- `404` — telpaal bestaat niet

---

#### `GET /api/v1/counting-points/top-busiest`

Top N drukste telpalen op een specifieke datum, gesorteerd op `TotalCounts` aflopend.

| Parameter | Verplicht | Standaard | Beschrijving                      |
| --------- | --------- | --------- | --------------------------------- |
| `date`    | Ja        | —         | `YYYY-MM-DD`, niet in de toekomst |
| `top`     | Nee       | `10`      | Aantal resultaten, max. 1000      |

```bash
curl "http://localhost:5000/api/v1/counting-points/top-busiest?date=2025-03-01&top=5"
```

```json
{
  "date": "2025-03-01",
  "top_n": 5,
  "count": 5,
  "items": [
    {
      "CountingPointID": 5070,
      "CountingPointName": "Gentbrugge brug",
      "TotalCounts": 1250
    }
  ]
}
```

---

### Weerstations (Weather Stations)

#### `GET /api/v1/weather-stations`

Lijst van alle weerstations gesorteerd op naam.

```json
{
  "count": 8,
  "items": [
    {
      "WeatherStationID": "6447",
      "Name": "Gent",
      "Latitude": 51.18,
      "Longitude": 3.82,
      "Altitude": 7.0
    }
  ]
}
```

---

#### `GET /api/v1/weather-stations/<station_id>`

Detail van één weerstation. `station_id` is de `WeatherStationID` (VARCHAR, bv. `"6447"`).

**Response 404** wanneer het station niet bestaat.

---

#### `GET /api/v1/weather-stations/<station_id>/wind`

Gemiddelde windsnelheid op 10 meter hoogte en de hoogste windvlaag voor een weerstation op een specifieke dag.

| Parameter | Verplicht | Beschrijving                                 |
| --------- | --------- | -------------------------------------------- |
| `date`    | Ja        | `YYYY-MM-DD`, mag niet in de toekomst liggen |

```bash
curl "http://localhost:5000/api/v1/weather-stations/6447/wind?date=2025-03-01"
```

```json
{
  "weather_station_id": "6447",
  "weather_station_name": "Gent",
  "date": "2025-03-01",
  "avg_wind_speed_10m": 4.2,
  "max_wind_gusts_speed": 12.5
}
```

**Foutgevallen:**

- `400` — datum ontbreekt, ongeldige notatie, of ligt in de toekomst
- `404` — weerstation bestaat niet

---

### Blue Bike-stations

#### `GET /api/v1/blue-bike-stations`

Lijst van alle Blue Bike-locaties gesorteerd op naam.

```json
{
  "count": 15,
  "items": [
    {
      "BlueBikeStationKey": 1,
      "LocationName": "Gent-Sint-Pieters",
      "Latitude": 51.04,
      "Longitude": 3.71
    }
  ]
}
```

---

#### `GET /api/v1/blue-bike-stations/<station_key>`

Detail van één Blue Bike-locatie. `station_key` is een integer (de surrogate key).

**Response 404** wanneer de locatie niet bestaat.

---

#### `GET /api/v1/blue-bike-stations/availability/last-7-days`

Per Blue Bike-locatie: het minimale en maximale aantal beschikbare fietsen in de afgelopen 7 dagen (exact 168 uur terug t.o.v. het huidige tijdstip).

```bash
curl "http://localhost:5000/api/v1/blue-bike-stations/availability/last-7-days"
```

```json
{
  "count": 15,
  "window": "last-7-days",
  "items": [
    {
      "blue_bike_station_key": 1,
      "location_name": "Gent-Sint-Pieters",
      "latitude": 51.04,
      "longitude": 3.71,
      "min_available": 2,
      "max_available": 24,
      "measurements": 336
    }
  ]
}
```

---

## Foutafhandeling

Alle foutresponses volgen dezelfde JSON-structuur:

```json
{
  "error": "Beschrijving van de fout",
  "status": 400,
  "details": "Optionele extra info"
}
```

| HTTP-code | Wanneer                                                            |
| --------- | ------------------------------------------------------------------ |
| `400`     | Ongeldige invoer (verkeerde parameterwaarde, datum in toekomst, …) |
| `404`     | Resource (telpaal, weerstation, station, job) bestaat niet         |
| `405`     | HTTP-methode niet toegelaten op dit pad                            |
| `409`     | Conflict — DWH-refresh loopt al                                    |
| `500`     | Onverwachte serverfout                                             |
| `503`     | Database niet bereikbaar (alleen bij `/health`)                    |

DB-fouten die via `RAISERROR` in een stored procedure gegenereerd worden, worden automatisch omgezet naar HTTP 400 (functionele fout) of HTTP 500 (technische fout).

---

## Validatieregels

De module [validators.py](validators.py) valideert alle invoer vóór aanroep van de stored procedure.

| Validator            | Regel                                                            |
| -------------------- | ---------------------------------------------------------------- |
| `parse_int`          | Waarde aanwezig en converteerbaar naar `int`                     |
| `parse_positive_int` | Zoals `parse_int`, maar ook `> 0`                                |
| `parse_date`         | Aanwezig en formaat `YYYY-MM-DD`                                 |
| `parse_period`       | Één van `day`, `week`, `month`, `year`                           |
| `require_past_date`  | Datum strikt kleiner dan vandaag (voor fietstellingen op dag)    |
| `require_not_future` | Datum kleiner dan of gelijk aan vandaag (voor wind, top-busiest) |

Path-parameters van het type `<int:id>` worden al door Flask zelf getypecheckt; ongeldige waarden geven direct een 404.

---

## Logging en metrics

De logging-vereisten uit de studiewijzer worden door twee mechanismen samen ingevuld:

| Vereiste                                       | Hoe gedekt                                      |
| ---------------------------------------------- | ----------------------------------------------- |
| Aantal keer dat elke operatie uitgevoerd werd  | `MetricsStore.count` via `GET /api/v1/metrics`  |
| Gemiddelde responstijd per operatie            | `MetricsStore.avg_ms` via `GET /api/v1/metrics` |
| Maximale responstijd per operatie              | `MetricsStore.max_ms` via `GET /api/v1/metrics` |
| Technische en functionele logging naar bestand | Rotating file log in `logging/webapi/`          |

### Bestandslog

Logging wordt geconfigureerd in [logging_setup.py](logging_setup.py). Bij het starten van de API wordt automatisch de map aangemaakt.

**Locatie:** `logging/webapi/webapi.log` (pad configureerbaar via `API_LOG_DIR`)

- Formaat: `YYYY-MM-DD HH:MM:SS [LEVEL] module: bericht`
- Rotatie: maximaal 2 MB per bestand, 5 backups behouden
- Bevat technische logs (INFO+) en één access-log-regel per request

**Access-log formaat per request:**

```text
remote=127.0.0.1 method=GET path="/api/v1/counting-points/5070/totals" status=200 duration_ms=34.21 endpoint=counting.get_counting_point_totals query="period=month"
```

Het log-niveau is instelbaar via `API_LOG_LEVEL` (standaard `INFO`).

### In-memory metrics

De module [metrics.py](metrics.py) bevat een thread-safe `MetricsStore` die per endpoint de aggregaten bijhoudt. De `after_request`-hook in [app.py](app.py) werkt de store bij na elke request.

Opvragen via `GET /api/v1/metrics`:

```json
{
  "generated_at": "2025-05-08T10:00:00Z",
  "total_requests": 123,
  "endpoints": {
    "GET counting.get_counting_point_totals": {
      "count": 10,
      "errors": 1,
      "avg_ms": 45.12,
      "min_ms": 22.05,
      "max_ms": 120.3,
      "last_status": 200
    }
  }
}
```

| Veld          | Beschrijving                            |
| ------------- | --------------------------------------- |
| `count`       | Totaal aantal aanroepen                 |
| `errors`      | Aantal aanroepen met HTTP-status ≥ 400  |
| `avg_ms`      | Gemiddelde responstijd in milliseconden |
| `min_ms`      | Snelste responstijd                     |
| `max_ms`      | Traagste responstijd                    |
| `last_status` | HTTP-statuscode van de laatste aanroep  |

Gebruik `DELETE /api/v1/metrics` om de tellers te resetten voor een schone demo bij de eindevaluatie.

---

## Stored Procedures

Alle SQL-logica zit in [sql/stored_procedures.sql](sql/stored_procedures.sql). De Python-laag in [db.py](db.py) roept stored procedures aan via `call_proc(proc_naam, params_tuple)` — een dunne wrapper rond `pyodbc` die resultaten teruggeeft als een lijst van Python-dicts.

Overzicht van de stored procedures:

| Procedure                           | Parameters                    | Geeft terug                                   |
| ----------------------------------- | ----------------------------- | --------------------------------------------- |
| `sp_HealthCheck`                    | —                             | DB-naam, servertijd, tabel-tellingen          |
| `sp_List_CountingPoints`            | —                             | Alle telpalen                                 |
| `sp_List_WeatherStations`           | —                             | Alle weerstations                             |
| `sp_List_BlueBikeStations`          | —                             | Alle Blue Bike-locaties                       |
| `sp_Countings_SincePeriodStart`     | `@CountingPointID`, `@Period` | Telpaal-totalen vanaf start van de periode    |
| `sp_Countings_OnDay`                | `@CountingPointID`, `@Date`   | Telpaal-totalen op een specifieke dag         |
| `sp_Weather_WindForDay`             | `@WeatherStationID`, `@Date`  | Gemiddelde en max windsnelheid op een dag     |
| `sp_BlueBike_AvailabilityLast7Days` | —                             | Min/max beschikbaarheid per locatie (7 dagen) |
| `sp_Countings_TopBusiestPoints`     | `@Date`, `@TopN`              | Top N telpalen op datum (DESC op TotalCounts) |

De stored procedures bevatten eigen `RAISERROR`-validatie (severity 16) als aanvulling op de Python-validatie.

---

## Testen

De API wordt manueel getest via **Postman**. Er is een Postman-collectie beschikbaar die alle endpoints bevat met voorbeeldwaarden voor zowel de happy paths als de foutgevallen (ongeldige datum, onbestaand station, enz.).

**Stappen:**

1. Importeer de Postman-collectie in Postman.
2. Stel de collectie-variabele `base_url` in op `http://localhost:5000` (lokaal) of op het adres van de Ubuntu VM.
3. Zorg dat de API draait en de database bereikbaar is.
4. Voer de requests uit via de "Run collection"-knop of individueel per request.

De interactieve **Swagger UI** op `GET /api/v1/docs` biedt een alternatief om requests rechtstreeks in de browser uit te voeren zonder Postman.

---

## Architectuur

```text
HTTP Request
    │
    ▼
app.py (before_request: timer starten)
    │
    ▼
Blueprint (health / counting / weather / bluebike / dwh / metrics / extras / docs)
    │
    ├── validators.py  ── parameter validatie
    │
    ├── db.py ── call_proc() ── pyodbc ── SQL Server (stored procedure)
    │
    └── JSON response
    │
    ▼
app.py (after_request: metrics opslaan + access-log schrijven)
```

**Ontwerpkeuzes:**

- **Stored procedures** voor alle queries: de SQL-logica is gescheiden van de Python-code en kan los getest worden.
- **pyodbc direct** (geen SQLAlchemy): stored procedures met `RAISERROR` en meerdere resultsets werken betrouwbaarder via een directe cursor.
- **Blueprints** per resource-type: elke resource (telpalen, weerstations, enz.) heeft zijn eigen bestand voor duidelijke scheiding.
- **Async DWH-refresh**: de pipeline draait in een achtergrond-thread zodat het HTTP-request onmiddellijk terugkeert met een `job_id`.
- **In-memory metrics**: eenvoudig en voldoende voor een single-process deployment; resetten via `DELETE /metrics` voor een schone demo.
