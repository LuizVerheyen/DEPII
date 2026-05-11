# Doel van deze test:
# - Controleren of fillDimCountingPoint() nieuwe telpalen correct omzet naar de DWH-structuur.
# - Controleren of LocationKey correct wordt gekoppeld en lege input goed wordt afgehandeld.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte telpaaldata en database-opvragingen.
# - Controle op kolommen, unieke keys, voorbeeldwaarden en lege input.

import unittest
from unittest.mock import patch

import pandas as pd

from data_gathering.telpalen.dimCountingPoint import fillDimCountingPoint


EXPECTED_COLUMNS = [
    "CountingPointID",
    "CustomID",
    "CountingPointName",
    "Latitude",
    "Longitude",
    "FirstData",
    "Granularity",
    "Directional",
    "DirectionNameIn",
    "DirectionNameOut",
    "DomainID",
    "DomainName",
    "Description",
    "LocationKey",
]


class TestDimCountingPoint(unittest.TestCase):
    @patch("data_gathering.telpalen.dimCountingPoint.getLocationKey")
    @patch("data_gathering.telpalen.dimCountingPoint.getData")
    @patch("data_gathering.telpalen.dimCountingPoint.haal_telpalen_volledig_op")
    def test_filldimcountingpoint_transforms_new_rows(
        self, mock_haal_telpalen, mock_get_data, mock_get_location_key
    ):
        # Geen bestaande data
        mock_get_data.return_value = pd.DataFrame()

        # Telpalen mock
        mock_haal_telpalen.return_value = pd.DataFrame(
            [
                {
                    "counting_point_id": 1001,
                    "customId": "CP-1",
                    "name": "Paal Gent",
                    "latitude": 51.05,
                    "longitude": 3.72,
                    "firstData": "2024-01-01",
                    "granularity": "day",
                    "directional": True,
                    "direction_name_in": "In",
                    "direction_name_out": "Out",
                    "domain_id": 10,
                    "domain_name": "Fiets",
                    "description": "Test paal 1",
                    "postcode": "9000",
                },
                {
                    "counting_point_id": 1002,
                    "customId": "CP-2",
                    "name": "Paal Brugge",
                    "latitude": 51.21,
                    "longitude": 3.22,
                    "firstData": "2024-01-02",
                    "granularity": "day",
                    "directional": False,
                    "direction_name_in": "In",
                    "direction_name_out": "Out",
                    "domain_id": 11,
                    "domain_name": "Fiets",
                    "description": "Test paal 2",
                    "postcode": "8000",
                },
            ]
        )

        # LocationKey mocken
        mock_get_location_key.side_effect = [10, 20]

        df = fillDimCountingPoint()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertTrue(df["CountingPointID"].is_unique)
        self.assertEqual(df.loc[0, "LocationKey"], 10)
        self.assertEqual(df.loc[1, "LocationKey"], 20)

    @patch("data_gathering.telpalen.dimCountingPoint.haal_telpalen_volledig_op")
    def test_filldimcountingpoint_returns_empty_dataframe_when_no_new_rows(self, mock_haal_telpalen):
        mock_haal_telpalen.return_value = pd.DataFrame()

        df = fillDimCountingPoint()

        self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()
