import pytest
from conftest import run_check, run_custom_check
from validation_utils import table

TABLE = 'DimDate'

COLUMNS = {
    "date_key": "DateKey",
    "day_of_month": "DayOfMonth",
    "month": "Month",
    "english_dayname_of_week": "EnglishDayNameOfWeek",
    "dutch_dayname_of_week": "DutchDayNameOfWeek",
    "english_month_name": "EnglishMonthName",
    "dutch_month_name": "DutchMonthName",
    "year": "Year"
}

check = table(TABLE)

CHECKS = [
    check("row_count_where", 2192, COLUMNS['date_key'], 20200101, 20251231),
    check("not_null", COLUMNS['date_key']),
    check("unique", COLUMNS['date_key']),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_DimDate(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "date_key, day_of_month, month, year, english_dayname_of_week, dutch_dayname_of_week, english_month_name, dutch_month_name",
    [
        (20200803, 3, 8, 2020, 'Monday', 'maandag', 'August', 'augustus'),
        (20210406, 6, 4, 2021, 'Tuesday', 'dinsdag', 'April', 'april'),
        (20220525, 25, 5, 2022, 'Wednesday', 'woensdag', 'May', 'mei'),
        (20230622, 22, 6, 2023, 'Thursday', 'donderdag', 'June', 'juni'),
        (20240712, 12, 7, 2024, 'Friday', 'vrijdag', 'July', 'juli'),
        (20250920, 20, 9, 2025, 'Saturday', 'zaterdag', 'September', 'september'),
    ]
)
def test_date_attributes(db, date_key, day_of_month, month, year,
                         english_dayname_of_week, dutch_dayname_of_week,
                         english_month_name, dutch_month_name):

    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['date_key']} = ?
        AND {COLUMNS['day_of_month']} = ?
        AND {COLUMNS['month']} = ?
        AND {COLUMNS['year']} = ?
        AND {COLUMNS['english_dayname_of_week']} = ?
        AND {COLUMNS['dutch_dayname_of_week']} = ?
        AND {COLUMNS['english_month_name']} = ?
        AND {COLUMNS['dutch_month_name']} = ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"controle datum {date_key}",
        sql=sql,
        expected=1,
        params=(date_key, day_of_month, month, year,
                english_dayname_of_week, dutch_dayname_of_week,
                english_month_name, dutch_month_name),
    )