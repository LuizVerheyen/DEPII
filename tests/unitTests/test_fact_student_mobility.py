# Doel van deze test:
# - Controleren of fillFactStudentMobility() de studentmobiliteit correct verwerkt naar de DWH-structuur.
# - Controleren of StudentKey, DateKey, TransportKey en DistanceKM correct worden afgeleid.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata en database-opvragingen.
# - Controle op kolommen, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal

import data_gathering.studentMobility.fetch_fact_studentmobility as fact_student_module

EXPECTED_COLUMNS = ["StudentKey", "DateKey", "TransportKey", "DistanceKM"]

class TestFactStudentMobility(unittest.TestCase):
    @patch.object(fact_student_module, "getData")
    @patch.object(fact_student_module.pd, "read_excel")
    def test_fill_fact_studentmobility_transforms_source_data(self, mock_read_excel, mock_get_data):
        # Mock brondata (let op: mapping in code!)
        mock_read_excel.return_value = pd.DataFrame([
            {"Naam": "Student A", "Begintijd": "2024-03-15", "Km": 10.0, "Vervoermiddel": "Fiets"},
            {"Naam": "Student B", "Begintijd": "2024-03-16", "Km": 15.0, "Vervoermiddel": "Openbaar vervoer - trein"},
        ])
        # Mock voor alle getData-calls in volgorde:
        mock_get_data.side_effect = [
            pd.DataFrame({"DateKey": [20240315, 20240316]}),  # validate_datekey_with_dim
            pd.DataFrame({"VehicleType": ["Fiets", "Trein"]}),  # ensure_transport_types
            pd.DataFrame({"StudentKey": [1, 2], "StudentName": ["Student A", "Student B"]}),  # DimStudent
            pd.DataFrame({"TransportKey": [100, 200], "VehicleType": ["Fiets", "Trein"]}),  # DimTransportType
        ]
        df = fact_student_module.fillFactStudentMobility().reset_index(drop=True)
        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "StudentKey"], 1)
        self.assertEqual(df.loc[1, "TransportKey"], 200)
        self.assertAlmostEqual(df.loc[0, "DistanceKM"], 10.0, places=6)

    @patch.object(fact_student_module, "getData")
    @patch.object(fact_student_module.pd, "read_excel")
    def test_fill_fact_studentmobility_is_deterministic(self, mock_read_excel, mock_get_data):
        mock_read_excel.return_value = pd.DataFrame([
            {"Naam": "Student A", "Begintijd": "2024-03-15", "Km": 10.0, "Vervoermiddel": "Fiets"},
        ])
        # 2x4 = 8 calls want de functie wordt 2x aangeroepen
        mock_get_data.side_effect = [
            pd.DataFrame({"DateKey": [20240315]}),
            pd.DataFrame({"VehicleType": ["Fiets"]}),
            pd.DataFrame({"StudentKey": [1], "StudentName": ["Student A"]}),
            pd.DataFrame({"TransportKey": [100], "VehicleType": ["Fiets"]}),
            pd.DataFrame({"DateKey": [20240315]}),
            pd.DataFrame({"VehicleType": ["Fiets"]}),
            pd.DataFrame({"StudentKey": [1], "StudentName": ["Student A"]}),
            pd.DataFrame({"TransportKey": [100], "VehicleType": ["Fiets"]}),
        ]
        df1 = fact_student_module.fillFactStudentMobility().reset_index(drop=True)
        df2 = fact_student_module.fillFactStudentMobility().reset_index(drop=True)
        assert_frame_equal(df1, df2)


if __name__ == "__main__":
    unittest.main()
