"""
Metrics + evidence logging for DS-STD-2026.1.

Two artifacts per run, plus a per-test JSON (the plan's "every test emits its
FULL log + results", no pass/fail-only):
  logs/<run_id>/requests.csv   — one row per HTTP attempt
  logs/<run_id>/tests.csv      — one row per probe (the summary)
  logs/<run_id>/tests/<id>.json — full per-test detail incl. its request rows
A run-level coverage.csv is written by the runner from the TestResults.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_id_now(prefix: str = "run") -> str:
    return prefix + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass
class RequestRecord:
    """One HTTP attempt."""
    ts_utc: str
    source_id: str
    category: str
    method: str
    url: str
    http_status: int | None
    outcome: str            # "success" | "failure"
    reason_category: str
    reason_detail: str
    error_type: str
    latency_ms: float
    resp_bytes: int
    records_parsed: int
    retry_after_s: float | None
    notes: str = ""


REQUEST_COLUMNS = [
    "ts_utc", "source_id", "category", "method", "url", "http_status",
    "outcome", "reason_category", "reason_detail", "error_type",
    "latency_ms", "resp_bytes", "records_parsed", "retry_after_s", "notes",
]


@dataclass
class TestResult:
    """One probe's verdict + evidence."""
    test_id: str
    category: str
    source_id: str
    label: str
    jurisdiction: str          # "CA" | 2-letter P/T | "multi"
    licence: str
    commercial_ok: str         # "yes" | "no-written-permission" | "non-commercial" | "conditional" | "unknown"
    retrievable: bool
    reason_category: str
    reason_detail: str = ""
    endpoint: str = ""
    fields_found: list[str] = field(default_factory=list)
    record_count: int | None = None
    station_count: int | None = None
    earliest_year: int | None = None
    latest_year: int | None = None
    span_years: int | None = None
    latency_ms: float | None = None
    sample: str = ""           # trimmed raw response sample (evidence)
    notes: str = ""
    requests: list[RequestRecord] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


TEST_COLUMNS = [
    "test_id", "category", "source_id", "label", "jurisdiction", "licence",
    "commercial_ok", "retrievable", "reason_category", "endpoint",
    "n_fields", "fields_found", "record_count", "station_count",
    "earliest_year", "latest_year", "span_years", "latency_ms",
    "n_requests", "reason_detail", "notes",
]

COVERAGE_COLUMNS = [
    "category", "source_id", "label", "jurisdiction", "retrievable",
    "reason_category", "n_fields", "record_count", "station_count",
    "earliest_year", "span_years", "latency_ms", "commercial_ok", "licence",
]


def _test_row(r: TestResult) -> list:
    return [
        r.test_id, r.category, r.source_id, r.label, r.jurisdiction, r.licence,
        r.commercial_ok, r.retrievable, r.reason_category, r.endpoint,
        len(r.fields_found), "|".join(r.fields_found), r.record_count,
        r.station_count, r.earliest_year, r.latest_year, r.span_years,
        r.latency_ms, len(r.requests), r.reason_detail, r.notes,
    ]


def _coverage_row(r: TestResult) -> list:
    return [
        r.category, r.source_id, r.label, r.jurisdiction, r.retrievable,
        r.reason_category, len(r.fields_found), r.record_count, r.station_count,
        r.earliest_year, r.span_years, r.latency_ms, r.commercial_ok, r.licence,
    ]


class ResultLog:
    """Append-only CSV + per-test JSON writer, keyed by run_id."""

    def __init__(self, run_id: str, logs_root: str):
        self.run_id = run_id
        self.dir = os.path.join(logs_root, run_id)
        self.tests_dir = os.path.join(self.dir, "tests")
        os.makedirs(self.tests_dir, exist_ok=True)
        self.requests_csv = os.path.join(self.dir, "requests.csv")
        self.tests_csv = os.path.join(self.dir, "tests.csv")
        self.coverage_csv = os.path.join(self.dir, "coverage.csv")

    @staticmethod
    def _append(path: str, columns: list[str], rows: list[list]) -> None:
        new = not (os.path.exists(path) and os.path.getsize(path) > 0)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(columns)
            for row in rows:
                w.writerow(row)

    def write_result(self, r: TestResult) -> None:
        """Persist one probe: request rows, summary row, and per-test JSON."""
        if r.requests:
            self._append(
                self.requests_csv, REQUEST_COLUMNS,
                [[getattr(rec, c) for c in REQUEST_COLUMNS] for rec in r.requests],
            )
        self._append(self.tests_csv, TEST_COLUMNS, [_test_row(r)])
        self._append(self.coverage_csv, COVERAGE_COLUMNS, [_coverage_row(r)])
        with open(os.path.join(self.tests_dir, f"{r.test_id}.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(r), f, indent=2, default=str)
