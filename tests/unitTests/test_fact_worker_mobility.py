# Doel van deze test:
# - Controleren of factWorkerMobility() emissies juist berekent uit mobiliteitsdata en transporttypes.
# - Controleren of de output dezelfde grain behoudt als de brondata.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte database-opvragingen.
# - Controle op structuur, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch, mock_open

from pandas.testing import assert_frame_equal
import pandas as pd

import data_gathering.mobiliteitsBevragingHOGENT.factMobilityWorker as fact_worker_module


EXPECTED_COLUMNS = [
    "WorkerID",
    "DateKey",
    "TransportKey",
    "TravelTime",
    "TravelDistance",
    "TotalEmission"
]


def fake_getdata(engine, query=None):

    if "DimWorkerMobility" in query:
        return pd.DataFrame({
            "WorkerID": [1, 2],
            "ResponseID": ["R1", "R2"],
            "RecordDate": [20240315, 20240316],
        })

    if "DimTransportType" in query:
        return pd.DataFrame({
            "TransportKey": [100, 200],
            "VehicleType": ["Fiets", "Trein"],
            "CO2PerKM": [0.0, 0.02],
        })

    return pd.DataFrame()


FAKE_METADATA = {
    "value_labels": {
        "labels4": {
            "1.0": "Wagen, bestelwagen of vrachtwagen alleen of met familieleden",
            "10.0": "Fiets of elektrische fiets (speed pedelec inbegrepen)",
            "15.0": "Trein"
        }
    }
}


class TestFactWorkerMobility(unittest.TestCase):

    @patch.object(fact_worker_module, "loadIN")
    @patch.object(fact_worker_module, "getData")
    @patch.object(fact_worker_module.json, "load")
    @patch.object(fact_worker_module.pd, "read_csv")
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    def test_factworkermobility_calculates_emission(
        self,
        mock_file,
        mock_read_csv,
        mock_json_load,
        mock_get_data,
        mock_loadin
    ):

        mock_read_csv.return_value = pd.DataFrame([
            {
                "RecordedDate": "15/03/2024 00:00",
                "ResponseId": "R1",
                "pendeltijd": 120,
                "pendelafstand": 8.5,
                "vervoermiddel": 100,
            },
            {
                "RecordedDate": "16/03/2024 00:00",
                "ResponseId": "R2",
                "pendeltijd": 300,
                "pendelafstand": 15.0,
                "vervoermiddel": 150,
            },
        ])

        mock_json_load.return_value = FAKE_METADATA

        mock_get_data.side_effect = fake_getdata

        df = fact_worker_module.factWorkerMobility().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)

        self.assertEqual(len(df), 2)

        self.assertEqual(df.loc[0, "WorkerID"], 1)
        self.assertEqual(df.loc[0, "DateKey"], 20240315)
        self.assertEqual(df.loc[0, "TransportKey"], 100)
        self.assertAlmostEqual(df.loc[0, "TotalEmission"], 0.0)

        self.assertEqual(df.loc[1, "WorkerID"], 2)
        self.assertEqual(df.loc[1, "TransportKey"], 200)
        self.assertAlmostEqual(df.loc[1, "TotalEmission"], 0.3)


    @patch.object(fact_worker_module, "loadIN")
    @patch.object(fact_worker_module, "getData")
    @patch.object(fact_worker_module.json, "load")
    @patch.object(fact_worker_module.pd, "read_csv")
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    def test_factworkermobility_is_deterministic(
        self,
        mock_file,
        mock_read_csv,
        mock_json_load,
        mock_get_data,
        mock_loadin
    ):

        mock_read_csv.return_value = pd.DataFrame([
            {
                "RecordedDate": "15/03/2024 00:00",
                "ResponseId": "R1",
                "pendeltijd": 10,
                "pendelafstand": 10.0,
                "vervoermiddel": 150,
            }
        ])

        mock_json_load.return_value = FAKE_METADATA

        mock_get_data.side_effect = fake_getdata

        first = fact_worker_module.factWorkerMobility()
        second = fact_worker_module.factWorkerMobility()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
