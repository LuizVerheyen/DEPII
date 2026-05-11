import pytest
from conftest import run_check, run_tolerance_check
from validation_utils import table

TABLE = 'FactStaffCommute'
COLUMNS = {
    "date_key": "DateKey",
    "employee_key": "StaffKey",
    "kilometers": "DistanceKM",
    "pk": "StaffCommuteKey"  # primaire sleutel
}

check = table(TABLE)

# --- Definieer de checks ---
CHECKS = [
    check("row_count_at_least", 0),
    check("not_null_all", [COLUMNS["date_key"], COLUMNS["employee_key"]]),
    check("no_empty_all", [COLUMNS["date_key"], COLUMNS["employee_key"]]),
    # Check op de echte primaire sleutel
    check("unique_key", [COLUMNS["pk"]]),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_factstaffcommute_checks(db, check_def):
    run_check(db, check_def)


# --- Dynamische som van kilometers per datum ophalen ---
def get_expected_distance(db, date_key):
    cursor = db.cursor()
    cursor.execute(f"""
        SELECT SUM({COLUMNS['kilometers']})
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} = ?
    """, (date_key,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0

@pytest.mark.parametrize(
    "date_key",
    [
        20240108,
        20240304,
        20240607,  
        20250219,  
        20250510,         
        20251112,                  
    ],
    ids=lambda x: str(x),
)
def test_factstaffcommute_distance_sum(db, date_key):
    expected_count = get_expected_distance(db, date_key)
    sql = f"""
        SELECT SUM({COLUMNS['kilometers']})
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} = ?
    """

    run_tolerance_check(
        db=db,
        table=TABLE,
        name=f"totaal aantal kilometers door medewerkers op {date_key}",
        sql=sql,
        expected=expected_count,
        tolerance=0.1,
        params=(date_key,),
    )