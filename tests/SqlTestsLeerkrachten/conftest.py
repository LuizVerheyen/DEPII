import sqlite3
import pytest
import operator
from collections import defaultdict
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}


VALIDATION_RESULTS = []

SERVER = os.getenv("DB_SERVER", "127.0.0.1,2222")
DATABASE = os.getenv("DB_NAME", "DEPI")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
USER = os.getenv("DB_USER", "sa")
PASSWORD = os.getenv("databasePWD")

@pytest.fixture(scope="session")
def db():

    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    conn = pyodbc.connect(conn_str)

    yield conn

    conn.close()

def record_result(table, name, expected, actual, success):
    VALIDATION_RESULTS.append({
        "table": table,
        "name": name,
        "expected": str(expected),
        "actual": actual,
        "success": success,
    })


def run_check(db, check):
    cursor = db.cursor()
    cursor.execute(check["sql"])
    row = cursor.fetchone()
    actual = row[0] if row else None

    success = OPS[check["op"]](actual, check["expected"])

    record_result(
        table=check["table"],
        name=check["name"],
        expected=f"{check['op']} {check['expected']}",
        actual=actual,
        success=success,
    )

    assert success, (
        f"[{check['table']}] {check['name']} mislukt\n"
        f"SQL: {check['sql']}\n"
        f"Verwacht: {check['op']} {check['expected']}\n"
        f"Gekregen: {actual}"
    )

def run_custom_check(db, table, name, sql, expected, params=None):
    cursor = db.cursor()
    if params is None:
        cursor.execute(sql)
    else:
        cursor.execute(sql, params)

    row = cursor.fetchone()
    actual = row[0] if row else None
    success = actual == expected

    record_result(
        table=table,
        name=name,
        expected=f"== {expected}",
        actual=actual,
        success=success,
    )

    assert success, (
        f"[{table}] {name} mislukt\n"
        f"SQL: {sql}\n"
        f"Verwacht: {expected}\n"
        f"Gekregen: {actual}"
    )


def pytest_sessionfinish(session, exitstatus):
    if not VALIDATION_RESULTS:
        return

    grouped = defaultdict(list)
    for result in VALIDATION_RESULTS:
        grouped[result["table"]].append(result)

    total_passed = 0
    total_failed = 0

    print("\n" + "=" * 70)
    print("VALIDATIERAPPORT PER TABEL")
    print("=" * 70)

    for table, results in grouped.items():
        passed = sum(r["success"] for r in results)
        failed = len(results) - passed

        total_passed += passed
        total_failed += failed

        print(f"\nTabel: {table}")
        print("-" * 70)
        print(f"Geslaagd: {passed}")
        print(f"Gefaald : {failed}")
        print(f"Totaal   : {len(results)}")

        for r in results:
            status = "OK" if r["success"] else "FAIL"
            print(
                f"  [{status}] {r['name']} | verwacht {r['expected']} | gekregen {r['actual']}"
            )

    print("\n" + "=" * 70)
    print("ALGEMENE SAMENVATTING")
    print("=" * 70)
    print(f"Totaal geslaagd: {total_passed}")
    print(f"Totaal gefaald : {total_failed}")
    print(f"Totaal checks  : {total_passed + total_failed}")
    print("=" * 70)

def run_range_check(db, table, name, sql, min_expected, max_expected, params=None):

    cursor = db.cursor()

    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)

    row = cursor.fetchone()
    actual = row[0] if row else None

    success = min_expected <= actual <= max_expected

    VALIDATION_RESULTS.append({
        "table": table,
        "name": name,
        "expected": f"{min_expected}..{max_expected}",
        "actual": actual,
        "success": success,
    })

    assert success, (
        f"[{table}] {name} mislukt\n"
        f"SQL: {sql}\n"
        f"Verwacht tussen {min_expected} en {max_expected}\n"
        f"Gekregen: {actual}"
    )

def run_tolerance_check(db, table, name, sql, expected, tolerance=0.01, params=None):
    cursor = db.cursor()

    if params is None:
        cursor.execute(sql)
    else:
        cursor.execute(sql, params)

    row = cursor.fetchone()
    actual = row[0] if row else None

    success = actual is not None and abs(float(actual) - float(expected)) <= tolerance

    record_result(
        table=table,
        name=name,
        expected=f"{expected} ± {tolerance}",
        actual=actual,
        success=success,
    )

    assert success, (
        f"[{table}] {name} mislukt\n"
        f"SQL: {sql}\n"
        f"Verwacht: {expected} ± {tolerance}\n"
        f"Gekregen: {actual}"
    )
