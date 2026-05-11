import pytest
from conftest import run_check, run_custom_check, run_tolerance_check
from validation_utils import table

TABLE = 'DimBlueBikeStation'
COLUMNS = {
    "id": "BlueBikeStationKey",
    "name": "LocationName",
    "latitude": "Latitude",
    "longitude": "Longitude"
}

check = table(TABLE)

CHECKS = [
    check("row_count_at_least", 0),
    check("not_null", COLUMNS['name']),
    check("no_empty", COLUMNS['name']),
    check("unique_key", [COLUMNS["latitude"], COLUMNS["longitude"]]),
    check("unique", COLUMNS["name"]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_dimbluebikestation_checks(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "province, expected_count",
    [
        ("Antwerpen", 40),
        ("Oost-Vlaanderen", 87),
        ("West-Vlaanderen", 21),
        ("Limburg", 21),
        ("Vlaams-Brabant", 74),
        ("Luik", 1),
        ("Henegouwen", 1),        
    ],
    ids=lambda x: str(x),
)
def test_bluebike_locations_count_per_province(db, province, expected_count):
    sql = f"""
        SELECT COUNT(*)
        FROM DimBlueBikeStation s
        JOIN DimLocation l ON s.LocationKey = l.LocationKey
        WHERE l.Province = ?
    """

    run_tolerance_check(
        db=db,
        table=TABLE,
        name=f"aantal BlueBike locaties in {province}",
        sql=sql,
        expected=expected_count,
        tolerance=2,
        params=(province,),
    )


@pytest.mark.parametrize(
    "zipcode, expected_count",
    [
        (9000, 3),
        (9051, 1),
        (9800, 2),
        (8500, 2),       
    ],
    ids=lambda x: str(x),
)
def test_bluebike_locations_count_in_zipcode(db, zipcode, expected_count):
    sql = f"""
        SELECT COUNT(*)
        FROM DimBlueBikeStation s
        JOIN DimLocation l ON s.LocationKey = l.LocationKey
        WHERE l.PostalCode = ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal BlueBike locaties in postcode {zipcode}",
        sql=sql,
        expected=expected_count,
        params=(zipcode,),
    )


@pytest.mark.parametrize(
    "word, expected_count",
    [
        ('%station%', 131)
    ],
    ids=lambda x: str(x),
)
def test_bluebike_locations_count_name_contains_station(db, word, expected_count):
    sql = f"""
        SELECT COUNT(*)
        FROM DimBlueBikeStation
        WHERE LocationName LIKE ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal BlueBike locaties met '{word}' in naam",
        sql=sql,
        expected=expected_count,
        params=(word,),
    )