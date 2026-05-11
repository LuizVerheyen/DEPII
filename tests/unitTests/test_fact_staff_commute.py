# Doel van deze test:
# - Controleren of fillFactStaffCommute() dagelijkse fietsritten juist omzet naar fact-rijen.
# - Controleren of enkel geldige afstanden en bestaande StaffKey/DateKey combinaties worden meegenomen.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte brondata en database-opvragingen.
# - Controle op structuur, filtering, voorbeeldwaarden en deterministische output.

import importlib
import sys
import unittest
from unittest.mock import patch

from pandas.testing import assert_frame_equal
import pandas as pd


MODULE_NAME = "data_gathering.email_fietsvergoeding.filler"
EXPECTED_COLUMNS = ["StaffKey", "DateKey", "Period", "DistanceKM"]


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
            del sys.modules[MODULE_NAME]
        return importlib.import_module(MODULE_NAME)


class TestFactStaffCommute(unittest.TestCase):
    def test_fillfactstaffcommute_builds_fact_rows(self):
        filler_module = import_filler_module()

        source_df = pd.DataFrame(
            [
                {
                    "PersoneelsID": 1001,
                    "periode": "jan/24",
                    "dag 1": "12,5",
                    "dag 2": "0",
                    "dag 3": None,
                },
                {
                    "PersoneelsID": 1002,
                    "periode": "feb/24",
                    "dag 1": "8,0",
                    "dag 2": None,
                    "dag 3": None,
                },
            ]
        )
        for day in range(4, 32):
            source_df[f"dag {day}"] = None

        db_side_effect = [
            pd.DataFrame({"StaffKey": [10, 20], "StaffID": ["1001", "1002"]}),
            pd.DataFrame(
                {
                    "DateKey": [20240101, 20240201],
                    "DayOfMonth": [1, 1],
                    "Month": [1, 2],
                    "Year": [2024, 2024],
                }
            ),
        ]

        with patch.object(filler_module.pd, "read_csv", return_value=source_df), patch.object(
            filler_module, "getData", side_effect=db_side_effect
        ), patch("builtins.print"):
            df = filler_module.fillFactStaffCommute().reset_index(drop=True)

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "StaffKey"], 10)
        self.assertEqual(df.loc[0, "DateKey"], 20240101)
        self.assertEqual(df.loc[0, "Period"], "jan/24")
        self.assertAlmostEqual(float(df.loc[0, "DistanceKM"]), 12.5, places=6)
        self.assertEqual(df.loc[1, "StaffKey"], 20)
        self.assertEqual(df.loc[1, "DateKey"], 20240201)

    def test_fillfactstaffcommute_is_deterministic(self):
        filler_module = import_filler_module()

        source_df = pd.DataFrame([{"PersoneelsID": 1001, "periode": "jan/24", "dag 1": "10,0"}])
        for day in range(2, 32):
            source_df[f"dag {day}"] = None

        db_return_values_one = [
            pd.DataFrame({"StaffKey": [10], "StaffID": ["1001"]}),
            pd.DataFrame(
                {
                    "DateKey": [20240101],
                    "DayOfMonth": [1],
                    "Month": [1],
                    "Year": [2024],
                }
            ),
        ]
        db_return_values_two = [
            pd.DataFrame({"StaffKey": [10], "StaffID": ["1001"]}),
            pd.DataFrame(
                {
                    "DateKey": [20240101],
                    "DayOfMonth": [1],
                    "Month": [1],
                    "Year": [2024],
                }
            ),
        ]

        with patch.object(filler_module.pd, "read_csv", return_value=source_df), patch.object(
            filler_module, "getData", side_effect=db_return_values_one
        ), patch("builtins.print"):
            first = filler_module.fillFactStaffCommute()

        with patch.object(filler_module.pd, "read_csv", return_value=source_df), patch.object(
            filler_module, "getData", side_effect=db_return_values_two
        ), patch("builtins.print"):
            second = filler_module.fillFactStaffCommute()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
