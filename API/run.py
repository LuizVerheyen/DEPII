"""Entry-point voor de Flask Web API.

Start lokaal:
    python -m API.run

Op de Ubuntu VM (productie-achtig) liefst via gunicorn:
    gunicorn --bind 0.0.0.0:5000 --workers 2 'API.app:create_app()'
"""

import sys

from API.app import create_app
from API.config import Config


def main():
    app = create_app()
    # Belangrijk: HOST = 0.0.0.0 zodat de API extern bereikbaar is op de VM.
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)


if __name__ == "__main__":
    sys.exit(main() or 0)
