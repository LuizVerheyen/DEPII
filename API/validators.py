"""Functionele invoer-validatie voor de API.

Dit zit bewust in een aparte module zodat de validatieregels op één plek
staan en gemakkelijk te testen zijn (eis 3.04).
"""

from datetime import date, datetime

from API.errors import APIError


VALID_PERIODS = ("day", "week", "month", "year")


def parse_int(value, name: str) -> int:
    if value is None:
        raise APIError(f"Parameter '{name}' is verplicht.", 400)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise APIError(f"Parameter '{name}' moet een geheel getal zijn.", 400)


def parse_positive_int(value, name: str) -> int:
    n = parse_int(value, name)
    if n <= 0:
        raise APIError(f"Parameter '{name}' moet groter dan 0 zijn.", 400)
    return n


def parse_date(value, name: str) -> date:
    if value is None:
        raise APIError(f"Parameter '{name}' is verplicht (formaat YYYY-MM-DD).", 400)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise APIError(
            f"Parameter '{name}' moet een geldige datum zijn in formaat YYYY-MM-DD.",
            400,
        )


def parse_period(value) -> str:
    if value is None:
        raise APIError(
            f"Parameter 'period' is verplicht. Toegelaten: {', '.join(VALID_PERIODS)}.",
            400,
        )
    v = str(value).lower()
    if v not in VALID_PERIODS:
        raise APIError(
            f"Ongeldige periode '{value}'. Toegelaten: {', '.join(VALID_PERIODS)}.",
            400,
        )
    return v


def require_past_date(d: date, name: str = "date") -> date:
    if d >= date.today():
        raise APIError(f"Parameter '{name}' moet in het verleden liggen.", 400)
    return d


def require_not_future(d: date, name: str = "date") -> date:
    if d > date.today():
        raise APIError(f"Parameter '{name}' mag niet in de toekomst liggen.", 400)
    return d
