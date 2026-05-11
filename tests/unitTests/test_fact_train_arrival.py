# Doel van deze test:
# - Controleren of fetch_and_upsert_staging() nieuwe treinritten juist in staging zet.
# - Controleren of promote_stable_to_fact() alleen stabiele tijdsvensters naar de fact-tabel doorstuurt.
#
# Gebruikte testmethode:
# - Unit test op de echte staging- en promotiefuncties met gemockte API-data, vaste tijd en database-opvragingen.
# - Controle op upsert-logica, tijdsvensters, tellingen en resterende stagingdata.

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

import data_gathering.NMBS.fetch_fact_trainarrival as trainarrival_module


class FakeDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 3, 21, 12, 0, 0)


class FakeJsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def make_unix(year, month, day, hour, minute):
    return int(datetime(year, month, day, hour, minute).timestamp())


class TestFactTrainArrival(unittest.TestCase):
    @patch.object(trainarrival_module.time, "sleep", return_value=None)
    @patch.object(trainarrival_module.requests, "get")
    @patch.object(trainarrival_module, "getData")
    def test_fetch_and_upsert_staging_updates_existing_records(self, mock_get_data, mock_requests_get, _mock_sleep):
        dim_station = pd.DataFrame(
            {
                "StationKey": [1, 2],
                "URI": ["BE.NMBS.0001", "BE.NMBS.0002"],
                "StationName": ["Gent", "Brugge"],
            }
        )
        existing_staging = pd.DataFrame(
            {
                "TrainID": ["IC1", "OLD1"],
                "StationKey": [1, 2],
                "DateKey": [20260321, 20260320],
                "TimeKey": [900, 800],
                "Delay": [0, 60],
                "Canceled": [False, False],
                "LastUpdated": [datetime(2026, 3, 21, 8, 0, 0), datetime(2026, 3, 20, 8, 0, 0)],
            }
        )
        mock_get_data.side_effect = [dim_station, existing_staging]
        mock_requests_get.side_effect = [
            FakeJsonResponse(
                {
                    "arrivals": {
                        "arrival": [
                            {
                                "vehicle": "IC1",
                                "time": str(make_unix(2026, 3, 21, 9, 0)),
                                "delay": "120",
                                "canceled": "0",
                            },
                            {
                                "vehicle": "IC2",
                                "time": str(make_unix(2026, 3, 21, 9, 15)),
                                "delay": "0",
                                "canceled": "1",
                            },
                        ]
                    }
                }
            ),
            FakeJsonResponse({"arrivals": {"arrival": []}}),
        ]

        with patch.object(trainarrival_module, "datetime", FakeDateTime), patch("builtins.print"):
            df = trainarrival_module.fetch_and_upsert_staging().reset_index(drop=True)

        self.assertEqual(len(df), 3)
        self.assertEqual(
            sorted(df["TrainID"].tolist()),
            ["IC1", "IC2", "OLD1"],
        )

        updated_ic1 = df[(df["TrainID"] == "IC1") & (df["StationKey"] == 1)].iloc[0]
        self.assertEqual(updated_ic1["Delay"], 120)
        self.assertFalse(updated_ic1["Canceled"])

        old_row = df[df["TrainID"] == "OLD1"].iloc[0]
        self.assertEqual(old_row["StationKey"], 2)

    @patch.object(trainarrival_module, "getData")
    def test_promote_stable_to_fact_moves_only_stable_windows(self, mock_get_data):
        staging_df = pd.DataFrame(
            {
                "TrainID": ["IC1", "IC2", "IC3"],
                "StationKey": [1, 1, 2],
                "DateKey": [20260321, 20260321, 20260321],
                "TimeKey": [900, 910, 1100],
                "Delay": [0, 0, 0],
                "Canceled": [False, True, False],
                "LastUpdated": [
                    datetime(2026, 3, 21, 9, 5, 0),
                    datetime(2026, 3, 21, 9, 10, 0),
                    datetime(2026, 3, 21, 11, 0, 0),
                ],
            }
        )
        station_keys = pd.DataFrame({"StationKey": [1, 2]})
        mock_get_data.side_effect = [staging_df, station_keys]

        with patch.object(trainarrival_module, "datetime", FakeDateTime), patch("builtins.print"):
            result = trainarrival_module.promote_stable_to_fact()

        self.assertIsNotNone(result)
        df_fact, df_remaining = result

        self.assertEqual(len(df_fact), 2)
        self.assertEqual(sorted(df_fact["StationKey"].tolist()), [1, 2])
        self.assertTrue((df_fact["DateKey"] == 20260321).all())
        self.assertTrue((df_fact["StartTime"] == 900).all())
        self.assertTrue((df_fact["EndTime"] == 930).all())

        station1 = df_fact[df_fact["StationKey"] == 1].iloc[0]
        station2 = df_fact[df_fact["StationKey"] == 2].iloc[0]
        self.assertEqual(station1["AmountOfArrivals"], 1)
        self.assertEqual(station2["AmountOfArrivals"], 0)

        self.assertEqual(len(df_remaining), 1)
        self.assertEqual(df_remaining.iloc[0]["TrainID"], "IC3")
        self.assertNotIn("ActualArrival", df_remaining.columns)

    @patch.object(trainarrival_module, "getData", return_value=pd.DataFrame())
    def test_promote_stable_to_fact_returns_none_when_staging_is_empty(self, _mock_get_data):
        with patch.object(trainarrival_module, "datetime", FakeDateTime), patch("builtins.print"):
            result = trainarrival_module.promote_stable_to_fact()

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
