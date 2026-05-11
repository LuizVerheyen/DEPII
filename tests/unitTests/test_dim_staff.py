# Doel van deze test:
# - Controleren of fillDimStaff() personeelsdata juist koppelt aan departementen.
# - Controleren of dubbele medewerkers maar één keer in de output terechtkomen.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata en database-opvraging.
# - Controle op kolommen, unieke StaffID's, voorbeeldwaarden en deterministische output.

import importlib
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal


EXPECTED_COLUMNS = ["StaffID", "DepartementKey", "Campus"]
MODULE_NAME = "data_gathering.email_fietsvergoeding.filler"


def build_import_csv():
    row = {"PersoneelsID": 1001, "periode": "jan/24"}
    for day in range(1, 32):
        row[f"dag {day}"] = None
    row["dag 1"] = "1,0"
    return pd.DataFrame([row])


def import_filler_module():
    import_csv = build_import_csv()
    import_side_effect = [
        pd.DataFrame({"StaffKey": [1], "StaffID": ["1001"]}),
        pd.DataFrame({"DateKey": [20240101], "DayOfMonth": [1], "Month": [1], "Year": [2024]}),
    ]

    with patch("pandas.read_csv", return_value=import_csv), patch(
        "DWH.connection.connect.getData", side_effect=import_side_effect
    ), patch("builtins.print"):
        if MODULE_NAME in sys.modules:
            return importlib.reload(sys.modules[MODULE_NAME])
        return importlib.import_module(MODULE_NAME)


class TestDimStaff(unittest.TestCase):
    def test_filldimstaff_maps_departments_and_removes_duplicates(self):
        filler_module = import_filler_module()

        source_df = pd.DataFrame(
            [
                {"PersoneelsID": 1001, "Entiteit": "DICT", "Hoofdcampus": "Campus A"},
                {"PersoneelsID": 1001, "Entiteit": "DICT", "Hoofdcampus": "Campus A"},
                {"PersoneelsID": 1002, "Entiteit": "DBT", "Hoofdcampus": "Campus B"},
            ]
        )
        dept_df = pd.DataFrame(
            {
                "DepartementKey": [10, 20],
                "DepartementName": ["DICT", "DBT"],
            }
        )

        with patch.object(filler_module.pd, "read_csv", return_value=source_df), patch.object(
            filler_module, "getData", return_value=dept_df
        ):
            df = filler_module.fillDimStaff().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertTrue(df["StaffID"].is_unique)
        self.assertEqual(df.loc[0, "StaffID"], 1001)
        self.assertEqual(df.loc[0, "DepartementKey"], 10)
        self.assertEqual(df.loc[1, "StaffID"], 1002)
        self.assertEqual(df.loc[1, "DepartementKey"], 20)

    def test_filldimstaff_is_deterministic(self):
        filler_module = import_filler_module()

        source_df = pd.DataFrame(
            [{"PersoneelsID": 1001, "Entiteit": "DICT", "Hoofdcampus": "Campus A"}]
        )
        dept_df = pd.DataFrame(
            {"DepartementKey": [10], "DepartementName": ["DICT"]}
        )

        with patch.object(filler_module.pd, "read_csv", return_value=source_df), patch.object(
            filler_module, "getData", return_value=dept_df
        ):
            first = filler_module.fillDimStaff()
            second = filler_module.fillDimStaff()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
