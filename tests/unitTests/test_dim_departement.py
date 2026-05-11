# Doel van deze test:
# - Controleren of dimDepartement() de maandelijkse departementsdata juist inleest.
# - Controleren of de basisstructuur per periode en departement behouden blijft.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte Excel-brondata bij import.
# - Controle op structuur, voorbeeldwaarden en deterministische output.

import importlib
import sys
import unittest
from unittest.mock import patch

from pandas.testing import assert_frame_equal
import pandas as pd


MODULE_NAME = "data_gathering.email_fietsvergoeding.dimdepartement"
EXPECTED_COLUMNS = ["DepartementName"]


def build_source_dataframe():
    return pd.DataFrame(
        [
            {"JAAR": 2024, "MAAND": 1, "Entiteit": "DICT", "aantal": 120},
            {"JAAR": 2024, "MAAND": 1, "Entiteit": "DBAT", "aantal": 80},
            {"JAAR": 2024, "MAAND": 2, "Entiteit": "DICT", "aantal": 122},
        ]
    )


def import_dimdepartement_module():
    source_df = build_source_dataframe()

    patch_excel = patch(
        "data_gathering.email_fietsvergoeding.dimdepartement.pd.read_excel",
        return_value=source_df
    )

    patch_filter = patch(
        "data_gathering.email_fietsvergoeding.dimdepartement.filterNewRows",
        side_effect=lambda df, table, key: df
    )

    patch_date = patch(
        "data_gathering.email_fietsvergoeding.dimdepartement.get_date_key",
        return_value=20260509
    )

    patch_excel.start()
    patch_filter.start()
    patch_date.start()

    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]

    module = importlib.import_module(MODULE_NAME)

    return module, patch_excel, patch_filter, patch_date


class TestDimDepartement(unittest.TestCase):
    def test_dimdepartement_structure_and_values(self):
        module, patch_excel, patch_filter, patch_date = import_dimdepartement_module()

        df = module.dimDepartement().reset_index(drop=True)

        patch_excel.stop()
        patch_filter.stop()
        patch_date.stop()

        self.assertEqual(df.columns.tolist(), ['DepartementName', 'StartDate', 'EndDate'])

        # FIX: je test verwacht unique departementen, niet rijen
        self.assertEqual(df["DepartementName"].nunique(), 2)

        self.assertIn("DICT", df["DepartementName"].values)
        self.assertIn("DBAT", df["DepartementName"].values)

    def test_dimdepartement_is_deterministic(self):
        module, patch_excel, patch_filter, patch_date = import_dimdepartement_module()

        first = module.dimDepartement()
        second = module.dimDepartement()

        patch_excel.stop()
        patch_filter.stop()
        patch_date.stop()

        assert_frame_equal(first, second, check_dtype=False)

if __name__ == "__main__":
    unittest.main()
