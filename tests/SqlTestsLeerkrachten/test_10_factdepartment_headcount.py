import pytest
from conftest import run_check, run_custom_check
from validation_utils import table

# Pas aan
TABLE = 'FactDepartement'
COLUMNS = {
    "date_key": "DateKey",
    "department_key": "DepartementKey",
    "headcount": "AmountOfWorkers"
}

check = table(TABLE)

CHECKS = [
    check("row_count_at_least", 0),
    check("not_null_all", [COLUMNS["date_key"], COLUMNS["department_key"]]),
    check("no_empty_all", [COLUMNS["date_key"], COLUMNS["department_key"]]),
    check("unique_key", [COLUMNS["date_key"], COLUMNS["department_key"]]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_FactDepartmentHeadcount(db, check_def):
    run_check(db, check_def)



def test_department_head_count_1(db):
    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} BETWEEN 20240101 AND 20241231
    """

# we hadden het dubbele er altijd insteken (verwijder alles en nog is opnieuw)
    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal records voor FactDepartmentHeadcount in 2024",
        sql=sql,
        expected=477
    )


def test_department_head_count_2(db):
    sql = f"""
        SELECT SUM({COLUMNS['headcount']})
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} BETWEEN 20240101 AND 20240131
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal werknemers voor FactDepartmentHeadcount in januari 2024",
        sql=sql,
        expected=2384
    )

def test_department_head_count_3(db):
    sql = f"""
        SELECT SUM({COLUMNS['headcount']})
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} BETWEEN 20250401 AND 20250430
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"aantal records voor FactDepartmentHeadcount in april 2025",
        sql=sql,
        expected=2300
    )
