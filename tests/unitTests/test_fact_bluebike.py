# Doel van deze test:
# - Controleren of factBlueBike() alleen geldige stations uit de dim meeneemt.
# - Controleren of datum, tijd en gekoppeld station correct worden toegevoegd.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte API-data, datum/tijd en database-opvragingen.
# - Controle op structuur, filtering en koppeling met een station.

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

import data_gathering.blueBikes.fetch_fact_bluebike as fact_bluebike_module


EXPECTED_COLUMNS = [
    "BlueBikeStationKey",
    "TotalBikesAvailable",
    "EBikesAvailable",
    "BlueBikesAvailable",
    "MaxCapacity",
    "BikesDefect",
    "BikesInUse",
    "DateKey",
    "TimeKey",
    "LinkedStationKey",
]


class TestFactBlueBike(unittest.TestCase):
    @patch.object(fact_bluebike_module, "get_linked_station_key", return_value=[101])
    @patch.object(fact_bluebike_module, "get_time_key", return_value=830)
    @patch.object(fact_bluebike_module, "get_date_key", return_value=20260321)
    @patch.object(fact_bluebike_module, "getData")
    @patch.object(fact_bluebike_module.pd, "read_json")
    def test_factbluebike_builds_fact_rows(
        self, mock_read_json, mock_get_data, _mock_date_key, _mock_time_key, _mock_linked_station_key
    ):
        mock_read_json.side_effect = [
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "total_bikes_available": 7,
                        "e_bikes_available": 2,
                        "blue_bikes_available": 5,
                        "max_capacity": 10,
                        "bikes_defect": 1,
                    },
                    {
                        "id": 2,
                        "total_bikes_available": 4,
                        "e_bikes_available": 1,
                        "blue_bikes_available": 3,
                        "max_capacity": 8,
                        "bikes_defect": 0,
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {"id": 1, "bikes_in_use": 3},
                    {"id": 2, "bikes_in_use": 1},
                ]
            ),
        ]
        mock_get_data.side_effect = [
            pd.DataFrame(
                {
                    "BlueBikeStationKey": [1],
                    "Latitude": [51.036],
                    "Longitude": [3.71],
                }
            ),
            pd.DataFrame(
                {
                    "StationKey": [101],
                    "Latitude": [51.036],
                    "Longitude": [3.71],
                }
            ),
        ]

        with patch.object(fact_bluebike_module, "datetime") as mock_datetime, patch("builtins.print"):
            mock_datetime.now.return_value = datetime(2026, 3, 21, 8, 30)
            df = fact_bluebike_module.factBlueBike().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "BlueBikeStationKey"], 1)
        self.assertEqual(df.loc[0, "DateKey"], 20260321)
        self.assertEqual(df.loc[0, "TimeKey"], 830)
        self.assertEqual(df.loc[0, "BikesInUse"], 3)
        self.assertEqual(df.loc[0, "LinkedStationKey"], 101)

    def test_get_linked_station_key_chooses_closest_station(self):
        df_bluebike = pd.DataFrame(
            {
                "Latitude": [51.036],
                "Longitude": [3.71],
            }
        )
        df_stations = pd.DataFrame(
            {
                "StationKey": [101, 102],
                "Latitude": [51.0361, 51.2],
                "Longitude": [3.7101, 3.5],
            }
        )

        result = fact_bluebike_module.get_linked_station_key(df_bluebike, df_stations, max_distance_m=500)

        self.assertEqual(result, [101])


if __name__ == "__main__":
    unittest.main()
