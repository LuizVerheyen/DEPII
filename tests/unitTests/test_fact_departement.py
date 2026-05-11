# Doel van deze test:
# - Controleren of factDepartement() de maandelijkse aantallen juist koppelt aan DepartementKey.
# - Controleren of DateKey correct wordt afgeleid uit jaar en maand.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte Excel-brondata bij import en gemockte DimDepartement-opvraging.
# - Controle op structuur, voorbeeldwaarden en deterministische output.

import importlib
import sys
import unittest
from unittest.mock import patch

from pandas.testing import assert_frame_equal
import pandas as pd


MODULE_NAME = "data_gathering.email_fietsvergoeding.dimdepartement"
EXPECTED_COLUMNS = ["DateKey", "DepartementKey", "AmountOfWorkers"]


def build_source_dataframe():
    return pd.DataFrame(
        [
            {"JAAR": 2024, "MAAND": 1, "Entiteit": "DICT", "aantal": 120},
            {"JAAR": 2024, "MAAND": 1, "Entiteit": "DBIT", "aantal": 80},
            {"JAAR": 2024, "MAAND": 2, "Entiteit": "DICT", "aantal": 122},
        ]
    )


def import_dimdepartement_module():
    source_df = build_source_dataframe()

    patch_excel = patch(
        "data_gathering.email_fietsvergoeding.dimdepartement.pd.read_excel",
        return_value=source_df
    )

    patch_excel.start()

    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]

    module = importlib.import_module(MODULE_NAME)

    return module, patch_excel


class TestFactDepartement(unittest.TestCase):
    def test_factdepartement_builds_monthly_snapshot_rows(self):
        module, patch_excel = import_dimdepartement_module()

        dim_keys = pd.DataFrame({
            "DepartementKey": [42, 43],
            "DepartementName": ["DICT", "DBIT"],
        })

        with patch(
            "data_gathering.email_fietsvergoeding.dimdepartement.getData",
            return_value=dim_keys
        ):
            df = module.factDepartement().reset_index(drop=True)

        patch_excel.stop()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 3)

        self.assertEqual(df.loc[0, "DateKey"], 20240101)
        self.assertEqual(df.loc[0, "DepartementKey"], 42)

    def test_factdepartement_is_deterministic(self):
        module, patch_excel = import_dimdepartement_module()

        dim_keys = pd.DataFrame({
            "DepartementKey": [42, 43],
            "DepartementName": ["DICT", "DBIT"],
        })

        with patch(
            "data_gathering.email_fietsvergoeding.dimdepartement.getData",
            return_value=dim_keys
        ):
            first = module.factDepartement()
            second = module.factDepartement()

        patch_excel.stop()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
