# Doel van deze test:
# - Controleren of load_and_preprocess_survey() de mobiliteitsbevraging juist omzet naar de DWH-structuur.
# - Controleren of datum, afstanden, vervoermiddel en LocationKey correct worden afgeleid.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata, postcodebron en locatiekoppeling.
# - Controle op kolommen, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility import dimWM


EXPECTED_COLUMNS = [
    "ResponseID",
    "RecordDate",
    "LocationKey",
    "Latitude",
    "Longitude",
    "WorkPlace",
    "WorkFunction",
    "WorkRegime",
    "HomeWork",
    "Finished",
]


class TestDimWorkerMobility(unittest.TestCase):

    @patch("data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility.getLocationKey")
    @patch("data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility.pd.read_csv")
    def test_dimWM_transforms_correctly(self, mock_read_csv, mock_get_location_key):

        mock_read_csv.return_value = pd.DataFrame([
            {
                "RecordedDate": "15/03/2024 00:00",
                "ResponseId": "R1",
                "LocationLatitude": 51047,
                "LocationLongitude": 37210,
                "werkplek": 10,
                "pendeltijd": 120,
                "pendelafstand": 85,
                "vervoermiddel": 10,
                "Finished": 10,
                "functie": 20,
                "werk__": 60,
                "thuiswerk": 10,
            },
            {
                "RecordedDate": "16/03/2024 00:00",
                "ResponseId": "R2",
                "LocationLatitude": 51198,
                "LocationLongitude": 32170,
                "werkplek": 30,
                "pendeltijd": 300,
                "pendelafstand": 150,
                "vervoermiddel": 15,
                "Finished": 0,
                "functie": 10,
                "werk__": 20,
                "thuiswerk": 30,
            },
        ])

        mock_get_location_key.side_effect = [10, 20]

        df = dimWM().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)

        self.assertEqual(df.loc[0, "RecordDate"], 20240315)
        self.assertEqual(df.loc[0, "ResponseID"], "R1")
        self.assertEqual(df.loc[0, "LocationKey"], 10)
        self.assertEqual(df.loc[0, "WorkPlace"], "Aalst")
        self.assertEqual(df.loc[0, "WorkFunction"], "Onderwijzend personeel")
        self.assertEqual(df.loc[0, "WorkRegime"], "100% (voltijdse betrekking)")
        self.assertEqual(df.loc[0, "HomeWork"], "Geen thuiswerk")
        self.assertEqual(df.loc[0, "Finished"], 1.0)

        self.assertEqual(df.loc[1, "RecordDate"], 20240316)
        self.assertEqual(df.loc[1, "ResponseID"], "R2")
        self.assertEqual(df.loc[1, "LocationKey"], 20)
        self.assertEqual(df.loc[1, "WorkPlace"], "Bijloke")
        self.assertEqual(df.loc[1, "WorkFunction"], "Administratief personeel")
        self.assertEqual(df.loc[1, "WorkRegime"], f"20% - 39%")
        self.assertEqual(df.loc[1, "HomeWork"], "Thuiswerk 1 dag/week")
        self.assertEqual(df.loc[1, "Finished"], 0.0)
        

    @patch("data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility.getLocationKey")
    @patch("data_gathering.mobiliteitsBevragingHOGENT.dimWorkerMobility.pd.read_csv")
    def test_dimWM_is_deterministic(self, mock_read_csv, mock_get_location_key):

        mock_read_csv.return_value = pd.DataFrame([
            {
                "RecordedDate": "15/03/2024 00:00",
                "ResponseId": "R1",
                "LocationLatitude": 51047,
                "LocationLongitude": 37210,
                "werkplek": 10,
                "pendeltijd": 120,
                "pendelafstand": 85,
                "vervoermiddel": 10,
                "Finished": 10,
                "functie": 20,
                "werk__": 60,
                "thuiswerk": 10,
            }
        ])

        mock_get_location_key.return_value = 10

        first = dimWM()
        second = dimWM()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()