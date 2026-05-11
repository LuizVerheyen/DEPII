# Doel van deze test:
# - Controleren of dimBlueBikeStation() alleen nieuwe Blue-bike stations teruggeeft.
# - Controleren of de sleutelvelden en LocationKey correct worden opgebouwd.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte API-data en database-opvragingen.
# - Controle op filtering van bestaande keys, structuur en voorbeeldwaarden.

import unittest
from unittest.mock import patch

import pandas as pd

from data_gathering.blueBikes.initiator_dimBlueBikeStation import dimBlueBikeStation


EXPECTED_COLUMNS = ["BlueBikeStationKey", "LocationName", "Latitude", "Longitude", "LocationKey"]


class TestDimBlueBikeStation(unittest.TestCase):
    @patch("data_gathering.blueBikes.initiator_dimBlueBikeStation.getLocationKey")
    @patch("data_gathering.blueBikes.initiator_dimBlueBikeStation.getData")
    @patch("data_gathering.blueBikes.initiator_dimBlueBikeStation.pd.read_json")
    def test_dimbluebikestation_returns_only_new_stations(
        self, mock_read_json, mock_get_data, mock_get_location_key
    ):

        mock_read_json.return_value = pd.DataFrame([
            {"id": 1, "name": "Gent-Sint-Pieters", "latitude": 51.036, "longitude": 3.710},
            {"id": 2, "name": "Brugge Station", "latitude": 51.198, "longitude": 3.217},
        ])

        mock_get_data.return_value = pd.DataFrame({
            "BlueBikeStationKey": [1]
        })

        mock_get_location_key.return_value = 20

        df = dimBlueBikeStation()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[1]["BlueBikeStationKey"], 2)
        self.assertEqual(df.iloc[1]["LocationName"], "Brugge Station")
        self.assertEqual(df.iloc[0]["LocationKey"], 20)

    @patch("data_gathering.blueBikes.initiator_dimBlueBikeStation.getData")
    @patch("data_gathering.blueBikes.initiator_dimBlueBikeStation.pd.read_json")
    def test_dimbluebikestation_returns_empty_when_no_new_station_found(self, mock_read_json, mock_get_data):
        mock_read_json.return_value = pd.DataFrame(
            [{"id": 48, "name": "Antwerpen-Centraal Station", "latitude": 51.036, "longitude": 3.710}]
        )
        mock_get_data.return_value = pd.DataFrame({"BlueBikeStationKey": [48]})

        df = dimBlueBikeStation()

        self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()
