# Doel van deze test:
# - Controleren of download_weather_for_date() de weerdata juist omzet naar de fact-structuur.
# - Controleren of DateKey correct wordt afgeleid uit de timestamp en lege brondata wordt afgehandeld.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte API-response en vaste datum.
# - Controle op structuur, voorbeeldwaarden en foutafhandeling.

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

import data_gathering.weather.initializer as weather_initializer


EXPECTED_COLUMNS = [
    "WeatherStationKey",
    "PrecipQuantity",
    "TempAvg",
    "TempMax",
    "TempMin",
    "TempGrassPt100Avg",
    "TempSoilAvg",
    "TempSoilAvg5cm",
    "TempSoilAvg10cm",
    "TempSoilAvg20cm",
    "TempSoilAvg50cm",
    "WindSpeed10m",
    "WindSpeedAvg30m",
    "WindGustsSpeed",
    "HumidityRelShelterAvg",
    "Pressure",
    "SunDuration",
    "ShortWaveFromSkyAvg",
    "SunIntAvg",
    "DateKey",
]


class FakeDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 3, 21, 12, 0, 0)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


CSV_TEXT = """FID,code,qc_flags,the_geom,timestamp,precip_quantity,temp_avg,temp_max,temp_min,temp_grass_pt100_avg,temp_soil_avg,temp_soil_avg_5cm,temp_soil_avg_10cm,temp_soil_avg_20cm,temp_soil_avg_50cm,wind_speed_10m,wind_speed_avg_30m,wind_gusts_speed,humidity_rel_shelter_avg,pressure,sun_duration,short_wave_from_sky_avg,sun_int_avg
1,AWS1,,POINT (50.1 4.2),2026-03-20 12:00:00,1.2,10.5,12.0,8.0,9.5,11.0,11.1,11.2,11.3,11.4,4.5,5.1,7.0,81.0,1012.0,6.5,150.0,180.0
"""


class TestFactMeteo(unittest.TestCase):
    @patch.object(weather_initializer, "datetime", FakeDateTime)
    @patch.object(weather_initializer.requests, "get", return_value=FakeResponse(CSV_TEXT))
    def test_download_weather_for_date_transforms_source_data(self, _mock_get):
        with patch("builtins.print"):
            df = weather_initializer.download_weather_for_date()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "WeatherStationKey"], "AWS1")
        self.assertEqual(df.loc[0, "DateKey"], 20260320)
        self.assertAlmostEqual(df.loc[0, "TempAvg"], 10.5, places=6)
        self.assertAlmostEqual(df.loc[0, "WindSpeed10m"], 4.5, places=6)

    @patch.object(weather_initializer, "datetime", FakeDateTime)
    @patch.object(weather_initializer.requests, "get", return_value=FakeResponse(""))
    def test_download_weather_for_date_returns_none_when_api_is_empty(self, _mock_get):
        with patch("builtins.print"):
            df = weather_initializer.download_weather_for_date()

        self.assertIsNone(df)


if __name__ == "__main__":
    unittest.main()
