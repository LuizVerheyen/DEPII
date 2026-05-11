"""OpenAPI/Swagger UI endpoints.

Routes:
    GET /api/v1/openapi.yaml  → de OpenAPI-specificatie
    GET /api/v1/docs          → Swagger UI (via CDN, geen extra dependencies)
"""

from flask import Blueprint, send_from_directory, Response
import os

bp = Blueprint("docs", __name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_OPENAPI_PATH = os.path.abspath(os.path.join(_HERE, os.pardir, "openapi.yaml"))


@bp.route("/openapi.yaml", methods=["GET"])
def openapi_yaml():
    folder = os.path.dirname(_OPENAPI_PATH)
    return send_from_directory(folder, os.path.basename(_OPENAPI_PATH), mimetype="application/yaml")


_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="nl">
  <head>
    <meta charset="utf-8" />
    <title>DEPI Web API – Swagger UI</title>
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: "/api/v1/openapi.yaml",
          dom_id: "#swagger-ui",
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis],
        });
      };
    </script>
  </body>
</html>
"""


@bp.route("/docs", methods=["GET"])
def swagger_ui():
    return Response(_SWAGGER_HTML, mimetype="text/html")
