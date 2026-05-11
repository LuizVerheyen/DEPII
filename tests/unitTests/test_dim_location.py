import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from data_gathering.dimLocation.initializer import dimLocation


EXPECTED_COLUMNS = ["PostalCode", "Municipality", "MainMunicipality", "Province"]
KEY_COLUMNS = ["PostalCode", "Municipality", "MainMunicipality", "Province"]


def fake_zipcodes():
    return pd.DataFrame([
        {
            "Postcode": 99999,
            "Plaatsnaam": "X_TEST_CITY_A",
            "Hoofdgemeente": "X_TEST_MUNI_A",
            "Provincie": "X_TEST_PROV_A"
        },
        {
            "Postcode": 88888,
            "Plaatsnaam": "X_TEST_CITY_B",
            "Hoofdgemeente": "X_TEST_MUNI_B",
            "Provincie": "X_TEST_PROV_B"
        },
        {
            "Postcode": 77777,
            "Plaatsnaam": "X_TEST_CITY_C",
            "Hoofdgemeente": "X_TEST_MUNI_C",
            "Provincie": "X_TEST_PROV_C"
        }
    ])


class TestDimLocation(unittest.TestCase):

    @patch("data_gathering.dimLocation.initializer.os.getcwd", return_value="/fake/project")
    @patch("pandas.read_excel", return_value=fake_zipcodes())
    def test_dimlocation_structure_and_keys(self, _excel, _cwd):

        df = dimLocation()

        # structuur
        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 3)
        self.assertEqual(df.duplicated(subset=KEY_COLUMNS).sum(), 0)

        # sanity check: mockdata effectief gebruikt
        self.assertIn("X_Test_City_A", df["Municipality"].values)


    @patch("data_gathering.dimLocation.initializer.os.getcwd", return_value="/fake/project")
    @patch("pandas.read_excel", return_value=fake_zipcodes())
    def test_dimlocation_known_rows(self, _excel, _cwd):

        df = dimLocation()

        city_a = df[
            (df["PostalCode"] == 99999) &
            (df["Municipality"] == "X_Test_City_A")
        ]
        self.assertEqual(len(city_a), 1)

        city_b = df[
            (df["PostalCode"] == 88888) &
            (df["Municipality"] == "X_Test_City_B")
        ]
        self.assertEqual(len(city_b), 1)

        city_c = df[
            (df["PostalCode"] == 77777) &
            (df["Municipality"] == "X_Test_City_C")
        ]
        self.assertEqual(len(city_c), 1)


    @patch("data_gathering.dimLocation.initializer.os.getcwd", return_value="/fake/project")
    @patch("pandas.read_excel", return_value=fake_zipcodes())
    def test_dimlocation_is_deterministic(self, _excel, _cwd):

        first = dimLocation()
        second = dimLocation()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()