import pytest
from conftest import run_check, run_range_check
from validation_utils import table, join_avg_sql_like

TABLE_LEFT = 'DimBlueBikeStation'
TABLE_RIGHT = 'FactBlueBike'

COLUMNS_LEFT = {
    "bluebikelocation_key": "BlueBikeStationKey",
    "name": "LocationName",
    "latitude": "Latitude",
    "longitude": "Longitude"
}

COLUMNS_RIGHT = {
    "date_key": "DateKey",
    "time_key": "TimeKey",
    "bluebikelocation_key": "BlueBikeStationKey",
    "bikes_available": "BlueBikesAvailable",
    "bikes_in_use": "BikesInUse"
}

check = table(TABLE_RIGHT)

CHECKS = [
    check("row_count_at_least", 0),
    check("not_null_all", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["time_key"], COLUMNS_RIGHT['bluebikelocation_key']]),
    check("no_empty_all", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["time_key"], COLUMNS_RIGHT['bluebikelocation_key']]),
    check("unique_key", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["time_key"], COLUMNS_RIGHT['bluebikelocation_key']]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_factbluebike_checks(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "location, min_count, max_count",
    [
        ("%Oostende%", 60, 80),
        ("%Deinze station%", 80, 115),
        ("%Ieper%", 5, 10),
        ("%Machelen%", 2, 15),
    ],
)
def test_factbluebike_locations_range(db, location, min_count, max_count):

    sql = join_avg_sql_like(
        COLUMNS_RIGHT["bikes_available"],
        TABLE_RIGHT,
        TABLE_LEFT,
        COLUMNS_RIGHT["bluebikelocation_key"],
        COLUMNS_LEFT["bluebikelocation_key"],
        COLUMNS_LEFT["name"],
    )

    run_range_check(
        db=db,
        table=TABLE_RIGHT,
        name=f"gemiddeld aantal beschikbare fietsen in {location}",
        sql=sql,
        min_expected=min_count,
        max_expected=max_count,
        params=(location,),
    )