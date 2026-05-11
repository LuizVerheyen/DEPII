import logging
import logging.handlers
import os

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")
_LOG_LEVEL = os.getenv("PIPELINE_LOG_LEVEL", "INFO")

_UNITTEST_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unitTests")
_UNITTEST_LOG_LEVEL = os.getenv("UNITTEST_LOG_LEVEL", "INFO")

# Configureert de root logger voor de data pipeline.
# Schrijft naar logging/pipeline/pipeline.log én naar de console.
# Roep dit éénmalig aan bij de start van de pipeline (initiator.py).
# Alle andere modules gebruiken gewoon logging.getLogger(__name__).
def setup_pipeline_logging() -> None:

    os.makedirs(_LOG_DIR, exist_ok=True)
    level = getattr(logging, _LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    # Voorkom dubbele handlers bij herhaalde aanroep
    root.handlers = [h for h in root.handlers if not getattr(h, "_pipeline_managed", False)]

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(_LOG_DIR, "pipeline.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._pipeline_managed = True
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console._pipeline_managed = True
    root.addHandler(console)

# Configureert logger voor unit tests
# Schrijven naar unittests.log
# Eenmalig aangeorepen vanuit conftest.py
def setup_unittest_logging() -> None:

    os.makedirs(_UNITTEST_LOG_DIR, exist_ok=True)
    level = getattr(logging, _UNITTEST_LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [h for h in root.handlers if not getattr(h, "_unittest_managed", False)]

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(_UNITTEST_LOG_DIR, "unittests.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._unittest_managed = True
    root.addHandler(file_handler)
