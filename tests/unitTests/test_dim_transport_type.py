# Doel van deze test:
# - Controleren of fillTransportType() de vaste transporttypes correct inleest.
# - Controleren of de gekende uitstootswaarden overeenkomen met het bronbestand.
#
# Gebruikte testmethode:
# - Unit test op de echte generatorfunctie met het bronbestand uit het project.
# - Controle op structuur, unieke transporttypes, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch

from pandas.testing import assert_frame_equal

from data_gathering.mobiliteitsBevragingHOGENT.dimTransportType import fillTransportType


EXPECTED_COLUMNS = ["VehicleType", "CO2PerKM"]
EXPECTED_VALUES = {
    "Trein": 0.02,
    "Bus": 0.03,
    "Auto": 0.15,
    "Vliegtuig-700": 0.2,
    "Vliegtuig+700": 0.3,
    "Vliegtuig+2500": 0.4,
    "Fiets": 0.0,
    "Boot": 0.0,
}

def fake_filter(df, table, key):
    return df  # BELANGRIJK: geen filtering in unit test


class TestDimTransportType(unittest.TestCase):
    @patch(
        "data_gathering.mobiliteitsBevragingHOGENT.dimTransportType.filterNewRows",
        side_effect=fake_filter
    )
    def test_dimtransporttype_structure_and_keys(self, _mock):
        df = fillTransportType()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 8)
        self.assertTrue(df["VehicleType"].is_unique)

    @patch(
        "data_gathering.mobiliteitsBevragingHOGENT.dimTransportType.filterNewRows",
        side_effect=fake_filter
    )
    def test_dimtransporttype_known_values(self, _mock):
        df = fillTransportType().set_index("VehicleType")

        for vehicle_type, expected_value in EXPECTED_VALUES.items():
            self.assertIn(vehicle_type, df.index)
            self.assertAlmostEqual(float(df.loc[vehicle_type, "CO2PerKM"]), expected_value, places=6)

    @patch(
        "data_gathering.mobiliteitsBevragingHOGENT.dimTransportType.filterNewRows",
        side_effect=fake_filter
    )
    def test_dimtransporttype_is_deterministic(self, _mock):
        first = fillTransportType()
        second = fillTransportType()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
