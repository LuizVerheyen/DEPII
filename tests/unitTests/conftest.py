import logging
import os
import sys

_LOGGING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logging"))
if _LOGGING_DIR not in sys.path:
    sys.path.insert(0, _LOGGING_DIR)

from logging_config import setup_unittest_logging

logger = logging.getLogger("unittest_runner")


def pytest_configure(config):
    setup_unittest_logging()
    logger.info("Unit test sessie gestart")


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    if report.passed:
        logger.info("PASS  %s", report.nodeid)
    elif report.failed:
        logger.error("FAIL  %s\n%s", report.nodeid, str(report.longrepr))
    elif report.skipped:
        logger.warning("SKIP  %s", report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    logger.info(
        "Unit test sessie afgesloten — exitstatus: %s | gefaald: %d",
        exitstatus,
        session.testsfailed,
    )
