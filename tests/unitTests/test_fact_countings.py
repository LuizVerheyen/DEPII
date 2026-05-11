# Doel van deze test:
# - Controleren of fillFactCountings() telgegevens juist omzet naar de fact-tabel.
# - Controleren of DateKey correct wordt afgeleid en lege input goed wordt afgehandeld.
#
# Gebruikte testmethode:
# - Unit test op de echte functie met gemockte database-opvragingen en teldata.
# - Controle op structuur, voorbeeldwaarden en gedrag bij lege input.

import importlib
import sys
import unittest
from unittest.mock import Mock, patch

import pandas as pd


MODULE_NAME = "data_gathering.telpalen.factCountings"
EXPECTED_COLUMNS = [
    "CountingPointID",
    "DateKey",
    "DirectionInCounts",
    "DirectionOutCounts",
    "TotalCounts",
]


def import_factcountings_module():
    import DWH.connection.connect as connect_module

    original_delete_data = getattr(connect_module, "deleteData", None)
    connect_module.deleteData = Mock()

    try:
        if MODULE_NAME in sys.modules:
            del sys.modules[MODULE_NAME]
        module = importlib.import_module(MODULE_NAME)
    finally:
        if original_delete_data is None:
            delattr(connect_module, "deleteData")
        else:
            connect_module.deleteData = original_delete_data

    return module


class TestFactCountings(unittest.TestCase):
    def test_fillfactcountings_transforms_counts(self):
        module = import_factcountings_module()
        dim_countingpoint = pd.DataFrame({"CountingPointID": [1001, 1002]})
        existing_count = pd.DataFrame({"aantal": [0]})
        source_counts = pd.DataFrame(
            {
                "CountingPointID": [1001, 1002],
                "Date": pd.to_datetime(["2026-03-20", "2026-03-21"]),
                "DirectionInCounts": [10, 15],
                "DirectionOutCounts": [12, 14],
                "TotalCounts": [22, 29],
            }
        )

        with patch.object(module, "getData", side_effect=[dim_countingpoint, existing_count]), patch.object(module, "haal_all_counts", return_value=[source_counts]), patch.object(module, "loadIN") as mock_load:
            result = module.fillFactCountings()


        self.assertIsNone(result)
        self.assertEqual(mock_load.call_count, 1)
        written_df = mock_load.call_args.kwargs["df"]

        self.assertEqual(written_df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(written_df), 2)
        self.assertEqual(written_df.loc[0, "CountingPointID"], 1001)
        self.assertEqual(written_df.loc[1, "CountingPointID"], 1002)
        self.assertEqual(written_df.loc[0, "DateKey"], 20260320)
        self.assertEqual(written_df.loc[1, "DateKey"], 20260321)
        self.assertEqual(written_df.loc[0, "DirectionInCounts"], 10)
        self.assertEqual(written_df.loc[1, "DirectionInCounts"], 15)
        self.assertEqual(written_df.loc[0, "DirectionOutCounts"], 12)
        self.assertEqual(written_df.loc[1, "DirectionOutCounts"], 14)
        self.assertEqual(written_df.loc[0, "TotalCounts"], 22)
        self.assertEqual(written_df.loc[1, "TotalCounts"], 29)

    def test_fillfactcountings_returns_dataframe_when_not_loading_to_db(self):
        module = import_factcountings_module()
        dim_countingpoint = pd.DataFrame({"CountingPointID": [1001]})
        existing_count = pd.DataFrame({"aantal": [0]})
        source_counts = pd.DataFrame(
            {
                "CountingPointID": [1001],
                "Date": pd.to_datetime(["2026-03-20"]),
                "DirectionInCounts": [10],
                "DirectionOutCounts": [12],
                "TotalCounts": [22],
            }
        )

        with patch.object(module, "getData", side_effect=[dim_countingpoint, existing_count]), \
             patch.object(module, "haal_all_counts", return_value=[source_counts]), \
             patch.object(module, "loadIN") as mock_load:
            result = module.fillFactCountings(load_to_db=False)

        mock_load.assert_not_called()
        self.assertIsNotNone(result)
        self.assertFalse(result.empty)
        self.assertEqual(result.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "CountingPointID"], 1001)
        self.assertEqual(result.loc[0, "DateKey"], 20260320)
        self.assertEqual(result.loc[0, "DirectionInCounts"], 10)
        self.assertEqual(result.loc[0, "DirectionOutCounts"], 12)
        self.assertEqual(result.loc[0, "TotalCounts"], 22)

    def test_fillfactcountings_returns_empty_when_dim_is_empty(self):
        module = import_factcountings_module()

        with patch.object(module, "getData", return_value=pd.DataFrame()):
            result = module.fillFactCountings()

        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
