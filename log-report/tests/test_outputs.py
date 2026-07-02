import json
from pathlib import Path

REPORT_PATH = Path("/app/report.json")
EXPECTED_KEYS = {"total_requests", "unique_ips", "top_path"}


def _load_report() -> dict:
    return json.loads(REPORT_PATH.read_text())


def test_report_exists():
    """Success criterion 1: /app/report.json exists."""
    assert REPORT_PATH.exists(), "no report.json found"


def test_report_schema():
    """Success criterion 2: valid JSON with exactly the required keys."""
    report = _load_report()
    assert set(report.keys()) == EXPECTED_KEYS, (
        f"expected keys {EXPECTED_KEYS}, got {set(report.keys())}"
    )


def test_total_requests():
    """Success criterion 3: total_requests equals 6."""
    report = _load_report()
    assert report["total_requests"] == 6, (
        f"expected total_requests=6, got {report['total_requests']}"
    )


def test_unique_ips():
    """Success criterion 4: unique_ips equals 3."""
    report = _load_report()
    assert report["unique_ips"] == 3, (
        f"expected unique_ips=3, got {report['unique_ips']}"
    )


def test_top_path():
    """Success criterion 5: top_path equals /index.html."""
    report = _load_report()
    assert report["top_path"] == "/index.html", (
        f"expected top_path='/index.html', got {report['top_path']!r}"
    )
