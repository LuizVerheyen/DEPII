# Logging

Centrale map voor alle logbestanden van het DEPI-project. Elke component schrijft naar een eigen submap.

## Structuur

```text
logging/
├── logging_config.py       # Gedeelde logging-configuratie (pipeline + unit tests)
├── pipeline/
│   └── pipeline.log        # ETL-pipeline (initiator.py)
├── webapi/
│   └── webapi.log          # Web API (Flask, access logs, metrics)
└── unitTests/
    └── unittests.log       # Unit tests (conftest.py)
```

## Logbestanden

| Bestand | Geschreven door | Formaat |
| --- | --- | --- |
| `pipeline/pipeline.log` | `logging_config.setup_pipeline_logging()` | `YYYY-MM-DD HH:MM:SS - <module> - LEVEL - bericht` |
| `webapi/webapi.log` | `api/logging_setup.configure_logging()` | `YYYY-MM-DD HH:MM:SS [LEVEL] <module>: bericht` |
| `unitTests/unittests.log` | `logging_config.setup_unittest_logging()` | `YYYY-MM-DD HH:MM:SS - <module> - LEVEL - bericht` |

Alle drie gebruiken een `RotatingFileHandler`: het logbestand wordt automatisch geroteerd wanneer het de maximale grootte bereikt.

| Logbestand | Max. grootte | Backups |
| --- | --- | --- |
| `pipeline.log` | 5 MB | 3 |
| `webapi.log` | 2 MB | 5 |
| `unittests.log` | 5 MB | 3 |

## Logniveau instellen

Het standaardniveau is `INFO`. Dit kan per component overschreven worden via omgevingsvariabelen in `.env`:

```env
PIPELINE_LOG_LEVEL=DEBUG
UNITTEST_LOG_LEVEL=WARNING
API_LOG_LEVEL=DEBUG
```

## Voorbeeldregels

**pipeline.log**

```text
2026-05-05 14:43:13,097 - __main__ - INFO - Fase 1: basislaag laden...
2026-05-05 14:43:15,210 - DWH.connection.validator - INFO - [ OK  ] DimTime (1440 rijen)
```

**webapi.log**

```text
2026-05-08 16:55:27,362 [INFO] API.app: Flask-app gemaakt. Routes geregistreerd onder /api/v1
2026-05-08 16:55:30,014 [INFO] API.app: ACCESS GET /api/v1/health 200 1ms
```

**unittests.log**

```text
2026-05-06 13:29:18,412 - unittest_runner - INFO - Unit test sessie gestart
2026-05-06 13:29:21,251 - unittest_runner - INFO - PASS  tests/unitTests/test_dim_bluebike_station.py
```
