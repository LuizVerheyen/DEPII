import pytest
from conftest import run_check, run_custom_check, run_range_check, run_tolerance_check
from validation_utils import table, join_count_sql_like_between


TABLE_LEFT = 'DimWeatherStation'
TABLE_RIGHT = 'FactMeteo'


COLUMNS_LEFT = {
    "weatherstation_key": "WeatherStationID",
    "weatherstation_name": "Name",
}

COLUMNS_RIGHT = {
    "date_key": "DateKey",
    "weatherstation_key": "WeatherStationKey",
    "precip_quantity": "PrecipQuantity",
    "avg_temp": "TempAvg",
    "max_temp": "TempMax",
    "min_temp": "TempMin",
}


check = table(TABLE_RIGHT)



CHECKS = [
    check("not_null_all", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT['weatherstation_key']]),
    check("unique_key", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT['weatherstation_key']]),
]


@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_fact_weatherstation(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "weatherstation_name, expected_count",
    [
        ("%BEITEM%", 2192),
        ("%BUZENOL%", 2192),
        ("%DE HAAN%", 300),
        ("%DIEPENBEEK%", 2192),
        ("%DOURBES%", 2192),
        ("%ERNAGE%", 2192),
        ("%HUMAIN%", 2192),
        ("%MELLE%", 2192),
        ("%MONT RIGI%", 2192),
        ("%RETIE%", 2192),
        ("%SINT-KATELIJNE-WAVER%", 2192),
        ("%STABROEK%", 2192),
        ("%UCCLE%", 2192),
        ("%ZEEBRUGGE%", 2192),
    ],
)
def test_weatherstation_measurement_count(db, weatherstation_name, expected_count):

    sql = join_count_sql_like_between(
        TABLE_RIGHT,
        TABLE_LEFT,
        COLUMNS_RIGHT["weatherstation_key"],
        COLUMNS_LEFT["weatherstation_key"],
        COLUMNS_LEFT["weatherstation_name"],
        COLUMNS_RIGHT["date_key"],
    )

    run_custom_check(
        db=db,
        table=TABLE_RIGHT,
        name=f"aantal metingen voor weerstation {weatherstation_name} tussen 20200101 en 20251231",
        sql=sql,
        expected=expected_count,
        params=(weatherstation_name, 20200101, 20251231),
    )


WEATHERSTATION_STATS = [
    {
        "weatherstation_name": "BEITEM",
        "max_temp_avg": 28.6,
        "min_temp_avg": -4.47,
        "max_temp_min": 22.03,
        "min_temp_min": -8.38,
        "min_temp_max": -3.66,
        "max_temp_max": 38.47,
        "avg_precip_quantity": 2.10691605839416,
    },

    {
        "weatherstation_name": "ZEEBRUGGE",
        "max_temp_avg": 28.55,
        "min_temp_avg": -3.3,
        "max_temp_min": 22.99,
        "min_temp_min": -6.01,
        "min_temp_max": -2.5,
        "max_temp_max": 34.97,
        "avg_precip_quantity": 1.48340328467153,
    },
]


@pytest.mark.parametrize(
    "station",
    WEATHERSTATION_STATS,
    ids=[s["weatherstation_name"] for s in WEATHERSTATION_STATS],
)

def test_weatherstation_statistics(db, station):

    station_name = station["weatherstation_name"]

    checks = [
        (
            "max gemiddelde temperatuur",
            f"""
            SELECT MAX(f.{COLUMNS_RIGHT['avg_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["max_temp_avg"],
        ),

        (
            "minimum gemiddelde temperatuur",
            f"""
            SELECT MIN(f.{COLUMNS_RIGHT['avg_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["min_temp_avg"],
        ),

        (
            "maximum van min temperatuur",
            f"""
            SELECT MAX(f.{COLUMNS_RIGHT['min_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["max_temp_min"],
        ),

        (
            "minimum van min temperatuur",
            f"""
            SELECT MIN(f.{COLUMNS_RIGHT['min_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["min_temp_min"],
        ),

        (
            "minimum van max temperatuur",
            f"""
            SELECT MIN(f.{COLUMNS_RIGHT['max_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["min_temp_max"],
        ),

        (
            "maximum van max temperatuur",
            f"""
            SELECT MAX(f.{COLUMNS_RIGHT['max_temp']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            AND f.{COLUMNS_RIGHT['date_key']} BETWEEN 20200101 AND 20251231
            """,
            station["max_temp_max"],
        ),

        (
            "gemiddelde neerslaghoeveelheid",
            f"""
            SELECT AVG(f.{COLUMNS_RIGHT['precip_quantity']})
            FROM {TABLE_RIGHT} f
            JOIN {TABLE_LEFT} d
            ON f.{COLUMNS_RIGHT['weatherstation_key']} = d.{COLUMNS_LEFT['weatherstation_key']}
            WHERE d.{COLUMNS_LEFT['weatherstation_name']} = ?
            """,
            station["avg_precip_quantity"],
        ),
    ]

    for metric_name, sql, expected_value in checks:

        run_tolerance_check(
            db=db,
            table=TABLE_RIGHT,
            name=f"{metric_name} voor weerstation {station_name}",
            sql=sql,
            expected=expected_value,
            tolerance=0.1,
            params=(station_name,),
        )