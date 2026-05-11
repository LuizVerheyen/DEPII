import pytest
from conftest import run_check, run_tolerance_check, run_custom_check
from validation_utils import table

# Pas aan
TABLE = "DimStation s JOIN DimLocation l ON s.LocationKey = l.LocationKey"
COLUMNS = {
    "trainstation_key": "s.StationKey",
    "trainstation_name": "s.StationName",
    "zipcode": "l.PostalCode",
    "municipality": "l.Municipality",
    "province": "l.Province",
    "latitude": "s.Latitude",
    "longitude": "s.Longitude"
}

check = table(TABLE)

CHECKS = [
    check("row_count", 125),
    check("not_null", COLUMNS['trainstation_name']),
    check("no_empty", COLUMNS['trainstation_name']),
    check("unique_key", [COLUMNS["latitude"], COLUMNS["longitude"]]),
    check("unique", COLUMNS["trainstation_name"]),
]


@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_countingpoints_locaties(db, check_def):
    run_check(db, check_def)

@pytest.mark.parametrize(
    "province, expected_count",
    [
        ("Antwerpen", 22),
        ("West-Vlaanderen", 18),
        ("Oost-Vlaanderen", 36),
        ("Vlaams-Brabant", 29),
        ("Limburg", 11),      
        ("Namen", 1),      
        ("Henegouwen", 1),              
    ],
    ids=lambda x: str(x),
)


def test_trainstations_locations_count_per_province(db, province, expected_count):
    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['province']} = ?
    """

    run_tolerance_check(
        db=db,
        table=TABLE,
        name=f"aantal records voor provincie {province}",
        sql=sql,
        expected=expected_count,
        tolerance=2,
        params=(province,),
    )

@pytest.mark.parametrize(
    "trainstation_name, expected_count",
    [
        ("%Antwerpen%", 5),
        ("%Ieper%", 1),
        ("%Lokeren%", 1),  
        ("%Lanaken%", 0),  
        ("%Zeebrugge%",2),         
        ("Testelt",1),                  
    ],
    ids=lambda x: str(x),
)

def test_trainstations_locations_count_in_municipality(db, trainstation_name, expected_count):
    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['trainstation_name']} LIKE ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal records voor treinstations in {trainstation_name}",
        sql=sql,
        expected=expected_count,
        params=(trainstation_name),
    )

