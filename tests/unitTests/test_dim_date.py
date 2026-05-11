# Doel van deze test:
# - Controleren of CreateDimDate() altijd dezelfde en volledige datumtabel opbouwt.
# - Controleren of enkele vaste datums de juiste afgeleide waarden krijgen.
#
# Gebruikte testmethode:
# - Unit test op de echte generatorfunctie, niet op handgemaakte testdata.
# - Mocking van de externe holiday API-calls zodat de test stabiel en herhaalbaar blijft.
# - Controle op structuur, bereik, voorbeeldwaarden en deterministische output.

import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from data_gathering.dimDate.initiator import CreateDimDate


EXPECTED_COLUMNS = [
    "DateKey",
    "FullDateAlternateKey",
    "DayOfMonth",
    "EnglishDayNameOfWeek",
    "DutchDayNameOfWeek",
    "DayOfWeek",
    "DayOfWeekInMonth",
    "DayOfWeekInYear",
    "DayOfQuarter",
    "DayOfYear",
    "WeekOfMonth",
    "WeekOfQuarter",
    "WeekOfYear",
    "Month",
    "EnglishMonthName",
    "DutchMonthName",
    "MonthOfQuarter",
    "Quarter",
    "QuarterName",
    "Year",
    "MonthYear",
    "MMYYYY",
    "IsHoliday",
    "HolidayName",
    "IsWeekend",
    "IsWorkingDay",
    "IsSchoolHoliday",
    "SchoolHolidayName",
]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def fake_requests_get(url):
    if "date.nager.at" in url:
        year = int(url.rstrip("/").split("/")[-2])
        return FakeResponse(
            [
                {"date": f"{year}-01-01", "localName": "Nieuwjaar"},
                {"date": f"{year}-12-25", "localName": "Kerstmis"},
            ]
        )

    if "openholidaysapi.org" in url:
        return FakeResponse(
            [
                {
                    "startDate": "2026-02-16",
                    "endDate": "2026-02-20",
                    "name": [{"text": "Krokusvakantie"}],
                },
                {
                    "startDate": "2026-07-01",
                    "endDate": "2026-08-31",
                    "name": [{"text": "Zomervakantie"}],
                },
            ]
        )

    raise AssertionError(f"Onverwachte URL in test: {url}")


class TestDimDate(unittest.TestCase):
    @patch("data_gathering.dimDate.initiator.filterNewRows")
    @patch("data_gathering.dimDate.initiator.requests.get", side_effect=fake_requests_get)
    def test_createdimdate_structure_and_range(self, _mock_get, mock_filter):
        mock_filter.side_effect = lambda df, table, key: df

        df = CreateDimDate()

        self.assertEqual(df.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(len(df), 6209)
        self.assertEqual(df["DateKey"].min(), 20100101)
        self.assertEqual(df["DateKey"].max(), 20261231)
        self.assertTrue(df["DateKey"].is_unique)

    @patch("data_gathering.dimDate.initiator.filterNewRows")
    @patch("data_gathering.dimDate.initiator.requests.get", side_effect=fake_requests_get)
    def test_createdimdate_known_dates(self, _mock_get, mock_filter):
        mock_filter.side_effect = lambda df, table, key: df

        df = CreateDimDate().set_index("DateKey")

        first_day = df.loc[20100101]
        self.assertEqual(first_day["EnglishDayNameOfWeek"], "Friday")
        self.assertEqual(first_day["DutchDayNameOfWeek"], "vrijdag")
        self.assertEqual(first_day["Month"], 1)
        self.assertEqual(first_day["EnglishMonthName"], "January")
        self.assertEqual(first_day["DutchMonthName"], "januari")
        self.assertEqual(first_day["QuarterName"], "Q1")

        last_day = df.loc[20261231]
        self.assertEqual(last_day["Year"], 2026)
        self.assertEqual(last_day["Month"], 12)
        self.assertEqual(last_day["DayOfMonth"], 31)
        self.assertEqual(last_day["EnglishDayNameOfWeek"], "Thursday")
        self.assertEqual(last_day["QuarterName"], "Q4")

    @patch("data_gathering.dimDate.initiator.filterNewRows")
    @patch("data_gathering.dimDate.initiator.requests.get", side_effect=fake_requests_get)
    def test_createdimdate_holiday_and_schoolholiday_flags(self, _mock_get, mock_filter):
        mock_filter.side_effect = lambda df, table, key: df

        df = CreateDimDate().set_index("DateKey")

        new_year = df.loc[20260101]
        self.assertTrue(new_year["IsHoliday"])
        self.assertEqual(new_year["HolidayName"], "Nieuwjaar")
        self.assertFalse(new_year["IsWorkingDay"])

        summer_break = df.loc[20260715]
        self.assertTrue(summer_break["IsSchoolHoliday"])
        self.assertEqual(summer_break["SchoolHolidayName"], "Zomervakantie")

        regular_day = df.loc[20260303]
        self.assertFalse(regular_day["IsHoliday"])
        self.assertFalse(regular_day["IsSchoolHoliday"])

    @patch("data_gathering.dimDate.initiator.filterNewRows")
    @patch("data_gathering.dimDate.initiator.requests.get", side_effect=fake_requests_get)
    def test_createdimdate_is_deterministic(self, _mock_get, mock_filter):
        mock_filter.side_effect = lambda df, table, key: df

        first = CreateDimDate()
        second = CreateDimDate()

        assert_frame_equal(first, second, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
