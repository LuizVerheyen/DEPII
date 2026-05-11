"""Extra REST-resources voor een hogere score op 3.03.

Deze resources hergebruiken bestaande stored procedures en demonstreren
een uitbreidbaar resource-model.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

from API.db import call_proc
from API.errors import APIError
from API.validators import parse_date, require_not_future, parse_positive_int

bp = Blueprint("extras", __name__)


@bp.route("/counting-points/top-busiest", methods=["GET"])
def top_busiest_counting_points():
    """Top N drukste telpalen op een gegeven datum.

    Query-params:
        date  (verplicht, YYYY-MM-DD, niet in de toekomst)
        top   (optioneel, 1..1000, default 10)
    """
    parsed_date = require_not_future(parse_date(request.args.get("date"), "date"))
    top_n = request.args.get("top", "10")
    parsed_top = parse_positive_int(top_n, "top")
    if parsed_top > 1000:
        raise APIError("Parameter 'top' mag max. 1000 zijn.", 400)

    rows = call_proc(
        "dbo.sp_Countings_TopBusiestPoints",
        (parsed_date, parsed_top),
    )
    return jsonify({
        "date": parsed_date.isoformat(),
        "top_n": parsed_top,
        "count": len(rows),
        "items": rows,
    }), 200
