import pytest
from conftest import run_check, run_custom_check
from validation_utils import table

# Pas aan
TABLE = "DimStaff"
COLUMNS = {
    "employee_key": "StaffKey",
    "employee_id": "StaffID",
    "campus": "Campus",
    "department_key": "DepartementKey"
}

check = table(TABLE)

CHECKS = [
    check("row_count_at_least", 1),
    check("not_null_all", [
        COLUMNS["employee_key"],
        COLUMNS["employee_id"],
        COLUMNS["campus"],
        COLUMNS["department_key"],
    ]),
    check("no_empty", COLUMNS["campus"]),
    check("unique", COLUMNS["employee_key"]),
    check("unique", COLUMNS["employee_id"]),
]


@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_DimEmployee(db, check_def):
    run_check(db, check_def)


def test_employee_keys_non_negative(db):
    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['employee_key']} < 0
           OR {COLUMNS['department_key']} < 0
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name="geen negatieve sleutels in DimStaff",
        sql=sql,
        expected=0,
    )
