"""Weerstation-endpoints (DimWeatherStation + FactMeteo).

LET OP: in deze DWH bestaat op DimWeatherStation alleen de bron-ID
WeatherStationID (VARCHAR). FactMeteo.WeatherStationKey bevat dezelfde
waarde als WeatherStationID (alleen in een ander datatype). Er is geen
aparte IDENTITY surrogate key.
"""

from flask import Blueprint, jsonify, request
import logging

from API.db import call_proc
from API.errors import APIError
from API.validators import parse_date, require_not_future

bp = Blueprint("weather", __name__)
log = logging.getLogger(__name__)


@bp.route("/weather-stations", methods=["GET"])
def list_weather_stations():
    rows = call_proc("dbo.sp_List_WeatherStations")
    return jsonify({"count": len(rows), "items": rows}), 200


@bp.route("/weather-stations/<station_id>", methods=["GET"])
def get_weather_station(station_id: str):
    """Detail van één weerstation (lookup op WeatherStationID)."""
    rows = call_proc("dbo.sp_List_WeatherStations")
    match = next(
        (r for r in rows if str(r.get("WeatherStationID")) == str(station_id)),
        None,
    )
    if not match:
        raise APIError(f"Weerstation {station_id} bestaat niet.", 404)
    return jsonify(match), 200


@bp.route("/weather-stations/<station_id>/wind", methods=["GET"])
def get_wind_for_day(station_id: str):
    """Gemiddelde windsnelheid (10m) en hoogste windvlaag op een dag.

    Vereist: ?date=YYYY-MM-DD (mag niet in de toekomst liggen).

    De path-parameter is de WeatherStationID (zelfde waarde die in
    FactMeteo.WeatherStationKey voorkomt). Wordt als string doorgegeven
    omdat de SP-parameter een VARCHAR(50) is.
    """
    date_str = request.args.get("date")
    parsed_date = require_not_future(parse_date(date_str, "date"))

    rows = call_proc(
        "dbo.sp_Weather_WindForDay",
        (str(station_id), parsed_date),
    )
    if not rows:
        raise APIError(f"Weerstation {station_id} bestaat niet.", 404)

    r = rows[0]
    return jsonify({
        "weather_station_id":    r.get("WeatherStationID"),
        "weather_station_name":  r.get("WeatherStationName"),
        "date":                  r.get("Date", parsed_date.isoformat()),
        "avg_wind_speed_10m":    r.get("AvgWindSpeed10m"),
        "max_wind_gusts_speed":  r.get("MaxWindGustsSpeed"),
    }), 200
