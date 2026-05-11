# Doel van deze test:
# - Controleren of download_aws_stations() een volledige snapshot van de weerstations opbouwt.
# - Controleren of LocationKey en SnapshotDate correct worden ingevuld.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte API-responses en locatiekoppeling.
# - Controle op structuur, voorbeeldwaarden, fallback-logica en foutafhandeling.

import unittest
from unittest.mock import patch

import pandas as pd

import data_gathering.weather.weatherstationInitializer as weatherstation_initializer


EXPECTED_COLUMNS = [
    "WeatherStationID",
    "Name",
    "Altitude",
    "Latitude",
    "Longitude",
    "Point",
    "LocationKey",
    "SnapshotDate",
]


class FakeResponse:
    def __init__(self, text="", payload=None):
        self.text = text
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeLLMResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, _prompt):
        return FakeLLMResponse(self.content)


CSV_TEXT = """FID,code,name,altitude,province,date_begin,date_end,the_geom
1,AWS1,Station A,12.5,X,2024-01-01,2024-12-31,POINT (50.1 4.2)
2,AWS2,Station B,15.0,Y,2024-01-01,2024-12-31,POINT (51.2 3.2)
"""


class TestDimWeatherStation(unittest.TestCase):
    @patch.object(weatherstation_initializer, "getLocationKey")
    @patch.object(weatherstation_initializer.requests, "get")
    def test_download_aws_stations_builds_snapshot(self, mock_requests_get, mock_get_location_key):
        mock_requests_get.return_value = FakeResponse(text=CSV_TEXT)
        mock_get_location_key.side_effect = [10, 20]

        with patch("builtins.print"):
            df = weatherstation_initializer.download_aws_stations()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertTrue(df["WeatherStationID"].is_unique)
        self.assertEqual(df.loc[0, "WeatherStationID"], "AWS1")
        self.assertEqual(df.loc[0, "LocationKey"], 10)
        self.assertEqual(df.loc[1, "WeatherStationID"], "AWS2")
        self.assertEqual(df.loc[1, "LocationKey"], 20)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Altitude"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Latitude"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Longitude"]))
        self.assertTrue((df["SnapshotDate"] == pd.Timestamp.now().normalize().date()).all())

    @patch.object(weatherstation_initializer.requests, "get", side_effect=Exception("API fout"))
    def test_download_aws_stations_returns_none_on_request_failure(self, _mock_requests_get):
        with patch("builtins.print"):
            df = weatherstation_initializer.download_aws_stations()

        self.assertIsNone(df)


if __name__ == "__main__":
    unittest.main()
