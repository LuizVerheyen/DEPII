import pytest
from conftest import run_check, run_tolerance_check, run_custom_check
from validation_utils import table

# Pas aan
TABLE = 'DimDepartement'

COLUMNS = {  
    "department_key": "DepartementKey",
    "department_name": "DepartementName"  
}

check = table(TABLE)
# we hebben een time waardoor dit een slowly changing dimension is.
CHECKS = [
    check("row_count", 40),
    check("not_null", COLUMNS['department_name']),
    check("no_empty", COLUMNS['department_name']),
    check("unique", COLUMNS["department_name"]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_countingpoints_locaties(db, check_def):
    run_check(db, check_def)