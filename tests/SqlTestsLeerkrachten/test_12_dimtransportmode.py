import pytest
from conftest import run_check, run_custom_check
from validation_utils import table

TABLE = 'DimTransportType'
COLUMNS = {
    "transport_mode": "VehicleType",
    "emission_CO2_per_km": "CO2PerKM"
}

check = table(TABLE)

CHECKS = [
    check("row_count_at_least", 0),
    check("not_null", COLUMNS['transport_mode']),
    check("unique", COLUMNS['transport_mode']),
]

@pytest.mark.parametrize("check_def", CHECKS, ids=[c["name"] for c in CHECKS])
def test_dimtransporttype_checks(db, check_def):
    run_check(db, check_def)


@pytest.mark.parametrize(
    "transport_mode, emission_CO2_per_km",
    [
        ("Trein", 0.02),
        ("Bus", 0.03),
        ("Auto", 0.15),
        ("Vliegtuig-700", 0.2),
        ("Vliegtuig+700", 0.3),
        ("Vliegtuig+2500", 0.4),                     
        ("Fiets", 0),       
        ("Boot", 0)               
    ]
)
def test_dimtransporttype_emission_values(db, transport_mode, emission_CO2_per_km):
    sql = f"""
        SELECT COUNT(*)
        FROM {TABLE}
        WHERE {COLUMNS['transport_mode']} = ?
        AND {COLUMNS['emission_CO2_per_km']} = ?
    """

    run_custom_check(
        db=db,
        table=TABLE,
        name=f"controle transport_mode {transport_mode}",
        sql=sql,
        expected=1,
        params=(transport_mode, emission_CO2_per_km),
    )