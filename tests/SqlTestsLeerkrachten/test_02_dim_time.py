import pytest
from conftest import run_check, run_custom_check
from validation_utils import table

TABLE = 'DimTime'

COLUMNS = {
    "time_key": "TimeKey",
    "hour": "Hour",
    "minute": "Minute"
}

check = table(TABLE)

CHECKS = [
    check("row_count", 1440),
    check("not_null", COLUMNS['time_key']),
    check("unique", COLUMNS['time_key']),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_DimTime(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "time_key, hour, minute",
    [
        (12, 0, 12),
        (157, 1, 57),
        (324, 3, 24),
        (641, 6, 41),
        (1110, 11, 10),
        (1503, 15, 3),
        (1637, 16, 37),
    ]
)
def test_time_attributes(db, time_key, hour, minute):

    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['time_key']} = ?
        AND {COLUMNS['hour']} = ?
        AND {COLUMNS['minute']} = ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"controle tijd {time_key}",
        sql=sql,
        expected=1,
        params=(time_key, hour, minute),
    )