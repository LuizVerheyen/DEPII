"""Centrale foutafhandeling: API-exceptions + Flask error-handlers."""

from flask import jsonify
import logging
import pyodbc

log = logging.getLogger(__name__)


class APIError(Exception):
    """Functionele fout die rechtstreeks naar JSON gestuurd mag worden."""

    def __init__(self, message: str, status_code: int = 400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict:
        body = {"error": self.message, "status": self.status_code}
        if self.details is not None:
            body["details"] = self.details
        return body


def register_error_handlers(app) -> None:
    @app.errorhandler(APIError)
    def _handle_api_error(err: APIError):
        log.warning("APIError: %s (status=%s)", err.message, err.status_code)
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(404)
    def _not_found(err):
        return jsonify({"error": "Resource niet gevonden", "status": 404}), 404

    @app.errorhandler(405)
    def _method_not_allowed(err):
        return jsonify({"error": "Methode niet toegelaten", "status": 405}), 405

    @app.errorhandler(pyodbc.Error)
    def _handle_pyodbc(err):
        # Pak de RAISERROR-tekst uit de SQL Server response.
        msg = str(err)
        # Detecteer functionele input-fouten (RAISERROR severity 16)
        is_functional = any(kw in msg for kw in (
            "Ongeldige", "moet bestaan", "moet in het verleden",
            "mag niet in de toekomst", "verplicht", "Telpaal met deze ID",
            "Weerstation met deze key", "TopN moet",
        ))
        status = 400 if is_functional else 500
        log.error("DB-fout: %s", msg)
        return jsonify({"error": "Databasefout", "details": msg, "status": status}), status

    @app.errorhandler(Exception)
    def _handle_unexpected(err):
        log.exception("Onverwachte fout: %s", err)
        return jsonify({"error": "Interne serverfout", "details": str(err), "status": 500}), 500
