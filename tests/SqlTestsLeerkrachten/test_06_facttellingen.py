import pytest
from conftest import run_check, run_custom_check, run_range_check
from validation_utils import table, join_avg_sql_like, join_count_sql_like_between, join_sum_sql_like_between

# Pas aan
TABLE_LEFT = 'DimCountingPoint'
TABLE_RIGHT = 'FactCountings'

COLUMNS_LEFT = {
    "counting_point_key": "CountingPointID",
    "counting_point_name": "CountingPointName",
    "latitude": "Latitude",
    "longitude": "Longitude"
}

COLUMNS_RIGHT = {
    "date_key": "DateKey",
    "counting_point_key": "CountingPointID",
    "direction_in_counts": "DirectionInCounts",
    "direction_out_counts": "DirectionOutCounts",
    "total_counts": "TotalCounts"
}

check = table(TABLE_RIGHT)

CHECKS = [
    check("row_count_at_least", 0),
    check("not_null_all", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["counting_point_key"]]),
    check("no_empty_all", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["counting_point_key"]]),
    check("unique_key", [COLUMNS_RIGHT["date_key"], COLUMNS_RIGHT["counting_point_key"]]),
]


@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_blue_bike_locaties(db, check_def):
    run_check(db, check_def)



@pytest.mark.parametrize(
    "location, min_count, max_count",
    [
        ("%Menenstraat (Zuid)%", 46, 1047),
        ("%Desguinlei (Zuid)%", 2, 56517),
        ("%Langerbruggestraat%", 13, 1234),
        ("%Fietsen Door De Bomen H%", 0, 16682),
        ("%Terminal Brussels Airport%", 26, 324),        
    ],
)

def test_locations_range(db, location, min_count, max_count):


    sql = join_avg_sql_like(
        COLUMNS_RIGHT["total_counts"],
        TABLE_RIGHT,
        TABLE_LEFT,
        COLUMNS_RIGHT["counting_point_key"],
        COLUMNS_LEFT["counting_point_key"],
        COLUMNS_LEFT["counting_point_name"],
    )

    run_range_check(
        db=db,
        table=TABLE_RIGHT,
        name=f"min en max getelde fietsers in {location}",
        sql=sql,
        min_expected=min_count,
        max_expected=max_count,
        params=(location,),
    )


@pytest.mark.parametrize(
    "counting_point_name, expected_count",
    [
    ("%Fintele%", 134070),
    ("%Jaagpad Bovenschelde%", 359952),
    ("%Dudzeelse Steenweg (West)%", 210686),
    ("%Lierseweg brug (Oost)%", 494815),
    ],
)
def test_telpalen_tellingen_sum(db, counting_point_name, expected_count):


    sql = join_sum_sql_like_between(
        TABLE_RIGHT,
        TABLE_LEFT,
        COLUMNS_RIGHT["counting_point_key"],
        COLUMNS_LEFT["counting_point_key"],
        COLUMNS_RIGHT["total_counts"],
        COLUMNS_LEFT["counting_point_name"],
        COLUMNS_RIGHT["date_key"],      
    )

    run_custom_check(
        db=db,
        table=TABLE_RIGHT,
        name=f"aantal getelde fietsers voor telpaal {counting_point_name} tussen 20220101 en 20231231",
        sql=sql,
        expected=expected_count,
        params=(counting_point_name, 20220101, 20231231),
    )

