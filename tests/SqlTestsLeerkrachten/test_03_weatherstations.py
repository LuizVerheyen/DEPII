import pytest
from conftest import run_check
from validation_utils import table

TABLE = 'DimWeatherStation'

COLUMNS = {
    "weatherstation_key": "WeatherStationKey",
    "weatherstation_name": "Name",
    "latitude": "Latitude",
    "longitude": "Longitude"
}

check = table(TABLE)

CHECKS = [
    check("row_count", 14),
    check("not_null", COLUMNS['weatherstation_name']),
    check("no_empty", COLUMNS['weatherstation_name']),
    check("unique", COLUMNS["latitude"]),
    check("unique", COLUMNS["longitude"]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_weatherstations(db, check_def):
    run_check(db, check_def)