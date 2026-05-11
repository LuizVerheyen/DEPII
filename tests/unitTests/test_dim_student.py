# Doel van deze test:
# - Controleren of fillDimStudent() de studentdimensie correct verwerkt naar de DWH-structuur.
# - Controleren of StudentName en DepartementKey correct worden afgeleid en unieke studenten worden behouden.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata en database-opvragingen.
# - Controle op kolommen, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal

import data_gathering.studentMobility.fetch_dim_student as dim_student_module

EXPECTED_COLUMNS = ["StudentName", "DepartementKey"]

class TestDimStudent(unittest.TestCase):
    @patch.object(dim_student_module, "getData")
    @patch.object(dim_student_module.pd, "read_excel")
    def test_fill_dim_student_transforms_source_data(self, mock_read_excel, mock_get_data):
        # Mock brondata
        mock_read_excel.return_value = pd.DataFrame([
            {"Naam": "Student A"},
            {"Naam": "Student B"},
            {"Naam": "Student A"},  # Duplicate
        ])
        # Mock voor alle getData-calls in volgorde:
        mock_get_data.side_effect = [
            pd.DataFrame({"DepartementKey": [10], "DepartementName": ["DIT"]})  # DimDepartement
        ]
        df = dim_student_module.fillDimStudent().reset_index(drop=True)
        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "StudentName"], "Student A")
        self.assertEqual(df.loc[0, "DepartementKey"], 10)

    @patch.object(dim_student_module, "getData")
    @patch.object(dim_student_module.pd, "read_excel")
    def test_fill_dim_student_is_deterministic(self, mock_read_excel, mock_get_data):
        mock_read_excel.return_value = pd.DataFrame([
            {"Naam": "Student A"},
        ])
        # 2x2 = 4 calls want de functie wordt 2x aangeroepen
        mock_get_data.return_value = pd.DataFrame({
            "DepartementKey": [10],
            "DepartementName": ["DIT"]
        })
        df1 = dim_student_module.fillDimStudent().reset_index(drop=True)
        df2 = dim_student_module.fillDimStudent().reset_index(drop=True)
        assert_frame_equal(df1, df2)


if __name__ == "__main__":
    unittest.main()
