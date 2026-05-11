"""Telpaal-endpoints (DimCountingPoint + FactCountings).

REST-resource:           /counting-points
Sub-resources:
    GET /counting-points                          → lijst
    GET /counting-points/<id>                     → detail
    GET /counting-points/<id>/totals?period=...   → totaal sinds periode-start
    GET /counting-points/<id>/totals?date=...     → totaal op specifieke datum
"""

from flask import Blueprint, jsonify, request
import logging

from API.db import call_proc
from API.errors import APIError
from API.validators import (
    parse_int, parse_period, parse_date, require_past_date,
)

bp = Blueprint("counting", __name__)
log = logging.getLogger(__name__)


@bp.route("/counting-points", methods=["GET"])
def list_counting_points():
    rows = call_proc("dbo.sp_List_CountingPoints")
    return jsonify({"count": len(rows), "items": rows}), 200


@bp.route("/counting-points/<int:point_id>", methods=["GET"])
def get_counting_point(point_id: int):
    rows = call_proc("dbo.sp_List_CountingPoints")
    match = next((r for r in rows if r.get("CountingPointID") == point_id), None)
    if not match:
        raise APIError(f"Telpaal {point_id} bestaat niet.", 404)
    return jsonify(match), 200


@bp.route("/counting-points/<int:point_id>/totals", methods=["GET"])
def get_counting_point_totals(point_id: int):
    """Twee modi:
        - ?period=day|week|month|year   → sinds start van die periode
        - ?date=YYYY-MM-DD              → op die specifieke dag (in verleden)
    Exact één van beide is verplicht.
    """
    parse_int(point_id, "counting_point_id")  # type-check (al int via routing)

    period = request.args.get("period")
    date_str = request.args.get("date")

    if period and date_str:
        raise APIError(
            "Geef ofwel 'period' ofwel 'date' op, niet beide.", 400,
        )

    if period is not None:
        parsed_period = parse_period(period)
        rows = call_proc(
            "dbo.sp_Countings_SincePeriodStart",
            (point_id, parsed_period),
        )
        if not rows:
            return jsonify({
                "counting_point_id": point_id,
                "period": parsed_period,
                "total_counts": 0,
                "direction_in": 0,
                "direction_out": 0,
            }), 200
        r = rows[0]
        return jsonify({
            "counting_point_id": r.get("CountingPointID", point_id),
            "period":            r.get("Period", parsed_period),
            "start_date":        r.get("StartDate"),
            "end_date":          r.get("EndDate"),
            "total_counts":      r.get("TotalCounts", 0),
            "direction_in":      r.get("DirectionInCounts", 0),
            "direction_out":     r.get("DirectionOutCounts", 0),
        }), 200

    if date_str is not None:
        parsed_date = require_past_date(parse_date(date_str, "date"))
        rows = call_proc(
            "dbo.sp_Countings_OnDay",
            (point_id, parsed_date),
        )
        if not rows:
            return jsonify({
                "counting_point_id": point_id,
                "date": parsed_date.isoformat(),
                "total_counts": 0,
                "direction_in": 0,
                "direction_out": 0,
            }), 200
        r = rows[0]
        return jsonify({
            "counting_point_id": r.get("CountingPointID", point_id),
            "date":              r.get("Date", parsed_date.isoformat()),
            "total_counts":      r.get("TotalCounts", 0),
            "direction_in":      r.get("DirectionInCounts", 0),
            "direction_out":     r.get("DirectionOutCounts", 0),
        }), 200

    raise APIError(
        "Verplichte query-parameter ontbreekt: 'period' (day|week|month|year) "
        "of 'date' (YYYY-MM-DD).",
        400,
    )
