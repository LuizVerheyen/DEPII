# Doel van deze test:
# - Controleren of dimTime() een volledige tijdstabel per minuut genereert.
# - Controleren of enkele vaste tijdstippen correct worden opgebouwd.
#
# Gebruikte testmethode:
# - Unit test op de echte generatorfunctie.
# - Controle op structuur, aantal rijen, unieke sleutels en voorbeeldwaarden.
# - Extra check dat herhaald uitvoeren dezelfde output geeft.

import unittest
from unittest.mock import patch

from pandas.testing import assert_frame_equal

from data_gathering.dimTime.initiator import dimTime


EXPECTED_COLUMNS = ["fullTime", "TimeKey", "Hour", "Minute", "AMPM", "Hour12"]

def fake_filter(df, table, key):
    return df  # BELANGRIJK: geen filtering in unit test


class TestDimTime(unittest.TestCase):
    @patch("data_gathering.dimTime.initiator.filterNewRows", side_effect=fake_filter)
    def test_dimtime_structure_and_range(self, _mock):
        df = dimTime()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 1440)
        self.assertTrue(df["TimeKey"].is_unique)
        self.assertEqual(df["TimeKey"].min(), 0)
        self.assertEqual(df["TimeKey"].max(), 2359)

    @patch("data_gathering.dimTime.initiator.filterNewRows", side_effect=fake_filter)
    def test_dimtime_known_time_values(self,_mock):
        df = dimTime().set_index("TimeKey")

        midnight = df.loc[0]
        self.assertEqual(str(midnight["fullTime"]), "00:00:00")
        self.assertEqual(midnight["Hour"], 0)
        self.assertEqual(midnight["Minute"], 0)
        self.assertEqual(midnight["AMPM"], "AM")
        self.assertEqual(midnight["Hour12"], 12)

        morning = df.loc[830]
        self.assertEqual(str(morning["fullTime"]), "08:30:00")
        self.assertEqual(morning["Hour"], 8)
        self.assertEqual(morning["Minute"], 30)
        self.assertEqual(morning["AMPM"], "AM")
        self.assertEqual(morning["Hour12"], 8)

        noon = df.loc[1200]
        self.assertEqual(str(noon["fullTime"]), "12:00:00")
        self.assertEqual(noon["Hour"], 12)
        self.assertEqual(noon["Minute"], 0)
        self.assertEqual(noon["AMPM"], "PM")
        self.assertEqual(noon["Hour12"], 12)

        last_minute = df.loc[2359]
        self.assertEqual(str(last_minute["fullTime"]), "23:59:00")
        self.assertEqual(last_minute["Hour"], 23)
        self.assertEqual(last_minute["Minute"], 59)
        self.assertEqual(last_minute["AMPM"], "PM")
        self.assertEqual(last_minute["Hour12"], 11)

    @patch("data_gathering.dimTime.initiator.filterNewRows", side_effect=fake_filter)
    def test_dimtime_is_deterministic(self, _mock):
        first = dimTime()
        second = dimTime()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
