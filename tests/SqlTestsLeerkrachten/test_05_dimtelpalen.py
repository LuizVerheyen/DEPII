import pytest
from conftest import run_check, run_custom_check, run_tolerance_check
from validation_utils import table

TABLE = 'DimCountingPoint'

COLUMNS = {
    "counting_point_key": "CountingPointID",
    "counting_point_name": "CountingPointName",
    "latitude": "Latitude",
    "longitude": "Longitude"
}

check = table(TABLE)

CHECKS = [
    check("row_count", 356),
    check("not_null", COLUMNS['counting_point_name']),
    check("no_empty", COLUMNS['counting_point_name']),
    check("unique", COLUMNS["counting_point_key"]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_countingpoints(db, check_def):
    run_check(db, check_def)