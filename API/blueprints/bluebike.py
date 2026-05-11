"""Blue Bike-endpoints (DimBlueBikeStation + FactBlueBike)."""

from flask import Blueprint, jsonify
import logging

from API.db import call_proc
from API.errors import APIError

bp = Blueprint("bluebike", __name__)
log = logging.getLogger(__name__)


@bp.route("/blue-bike-stations", methods=["GET"])
def list_blue_bike_stations():
    rows = call_proc("dbo.sp_List_BlueBikeStations")
    return jsonify({"count": len(rows), "items": rows}), 200


@bp.route("/blue-bike-stations/<int:station_key>", methods=["GET"])
def get_blue_bike_station(station_key: int):
    rows = call_proc("dbo.sp_List_BlueBikeStations")
    match = next((r for r in rows if r.get("BlueBikeStationKey") == station_key), None)
    if not match:
        raise APIError(f"Blue Bike-station {station_key} bestaat niet.", 404)
    return jsonify(match), 200


@bp.route("/blue-bike-stations/availability/last-7-days", methods=["GET"])
def availability_last_7_days():
    """Min en max aantal beschikbare fietsen per locatie in de laatste 7 dagen."""
    rows = call_proc("dbo.sp_BlueBike_AvailabilityLast7Days")
    return jsonify({
        "count": len(rows),
        "window": "last-7-days",
        "items": [
            {
                "blue_bike_station_key": r.get("BlueBikeStationKey"),
                "location_name":         r.get("LocationName"),
                "latitude":              r.get("Latitude"),
                "longitude":             r.get("Longitude"),
                "min_available":         r.get("MinAvailable"),
                "max_available":         r.get("MaxAvailable"),
                "measurements":          r.get("Measurements"),
            }
            for r in rows
        ],
    }), 200
