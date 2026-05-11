# Doel van deze test:
# - Controleren of dimStation() stations kiest die dicht genoeg bij Blue-bike locaties liggen.
# - Controleren of dubbele stations worden verwijderd en LocationKey correct wordt ingevuld.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata, afstandsberekening en database-opvragingen.
# - Controle op structuur, filtering op afstand en voorbeeldwaarden.

import unittest
from unittest.mock import patch

import pandas as pd

from data_gathering.NMBS.initiator_dimStation import dimStation


EXPECTED_COLUMNS = ["URI", "StationName", "Latitude", "Longitude", "LocationKey"]


class TestDimStation(unittest.TestCase):
    @patch("data_gathering.NMBS.initiator_dimStation.getLocationKey")
    @patch("data_gathering.NMBS.initiator_dimStation.check_distance")
    @patch("data_gathering.NMBS.initiator_dimStation.getData")
    @patch("data_gathering.NMBS.initiator_dimStation.pd.read_csv")
    def test_dimstation_returns_nearby_stations(
        self, mock_read_csv, mock_get_data, mock_check_distance, mock_get_location_key
    ):
        mock_read_csv.return_value = pd.DataFrame(
            [
                {
                    "URI": "http://irail.be/stations/NMBS/0088",
                    "name": "Gent-Sint-Pieters2",
                    "latitude": 51.036,
                    "longitude": 3.710,
                },
                {
                    "URI": "http://irail.be/stations/NMBS/0089",
                    "name": "Brugge2",
                    "latitude": 51.198,
                    "longitude": 3.217,
                },
            ]
        )
        
        mock_get_data.side_effect = [
            pd.DataFrame(
                {
                    "BlueBikeStationKey": [1, 2],
                    "Latitude": [51.036, 51.198],
                    "Longitude": [3.710, 3.217],
                }
            ),
            pd.DataFrame(
                {
                    "LocationKey": [10, 20],
                    "PostalCode": ["9000", "8000"],
                    "Municipality": ["Gent", "Brugge"],
                }
            ),
        ]
        mock_check_distance.return_value = pd.Series([100, 900, 900, 120])
        mock_get_location_key.side_effect = [10, 20]

        df = dimStation().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertTrue(df["URI"].is_unique)
        self.assertEqual(df.loc[0, "URI"], "0088")
        self.assertEqual(df.loc[0, "LocationKey"], 10)
        self.assertEqual(df.loc[1, "URI"], "0089")
        self.assertEqual(df.loc[1, "LocationKey"], 20)

    @patch("data_gathering.NMBS.initiator_dimStation.getLocationKey")
    @patch("data_gathering.NMBS.initiator_dimStation.check_distance")
    @patch("data_gathering.NMBS.initiator_dimStation.getData")
    @patch("data_gathering.NMBS.initiator_dimStation.pd.read_csv")
    def test_dimstation_removes_duplicate_station_rows(
        self, mock_read_csv, mock_get_data, mock_check_distance, mock_get_location_key
    ):
        mock_read_csv.return_value = pd.DataFrame(
            [
                {
                    "URI": "http://irail.be/stations/NMBS/0088",
                    "name": "Gent-Sint-Pieters2",
                    "latitude": 51.036,
                    "longitude": 3.710,
                },
                {
                    "URI": "http://irail.be/stations/NMBS/0089",
                    "name": "Brugge2",
                    "latitude": 51.198,
                    "longitude": 3.217,
                },
            ]
        )
        mock_get_data.side_effect = [
            pd.DataFrame(
                {
                    "BlueBikeStationKey": [1, 2],
                    "Latitude": [51.036, 51.037],
                    "Longitude": [3.710, 3.711],
                }
            ),
            pd.DataFrame(
                {
                    "LocationKey": [10],
                    "PostalCode": ["9000"],
                    "Municipality": ["Gent"],
                }
            ),
        ]
        mock_check_distance.return_value = pd.Series([100, 900, 120, 950])
        mock_get_location_key.return_value = 10

        df = dimStation()

        self.assertEqual(len(df), 1)
        self.assertTrue(df["URI"].is_unique)
        self.assertEqual(df.iloc[0]["StationName"], "Gent-Sint-Pieters2")

    @patch("data_gathering.NMBS.initiator_dimStation.getLocationKey")
    @patch("data_gathering.NMBS.initiator_dimStation.check_distance")
    @patch("data_gathering.NMBS.initiator_dimStation.getData")
    @patch("data_gathering.NMBS.initiator_dimStation.pd.read_csv")
    def test_dimstation_excludes_stations_beyond_500m(
        self, mock_read_csv, mock_get_data, mock_check_distance, mock_get_location_key
    ):
        """Stations die verder dan 500m van alle Blue-bike locaties liggen worden niet opgenomen."""
        mock_read_csv.return_value = pd.DataFrame(
            [
                {
                    "URI": "http://irail.be/stations/NMBS/008811189",
                    "name": "Gent-Sint-Pieters",
                    "latitude": 51.036,
                    "longitude": 3.710,
                }
            ]
        )
        mock_get_data.side_effect = [
            pd.DataFrame(
                {
                    "BlueBikeStationKey": [1],
                    "Latitude": [51.100],
                    "Longitude": [3.800],
                }
            ),
            pd.DataFrame(
                {
                    "LocationKey": [10],
                    "PostalCode": ["9000"],
                    "Municipality": ["Gent"],
                }
            ),
        ]
        # Enige cross-rij: afstand > 500m → station wordt gefilterd
        mock_check_distance.return_value = pd.Series([1200])

        df = dimStation()

        self.assertEqual(len(df), 0)
        mock_get_location_key.assert_not_called()


if __name__ == "__main__":
    unittest.main()
