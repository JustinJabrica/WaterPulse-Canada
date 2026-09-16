"""
Probe contract shared by every source module.

A source module registers one or more probes with `@register(...)`. Each
probe is an `async def fn(spec, ctx) -> TestResult` that:
  1. fetches a small, SANCTIONED sample from the source (one bulk file / one
     API page / one SQLite read),
  2. records every HTTP attempt via `http_probe(...)`,
  3. inventories the fields returned + counts + historical depth,
  4. returns `spec.result(retrievable=..., reason_category=..., ...)`.

Keep probes low-load and read-only. Mark scrape/touchy sources
`sanctioned=False` so `probe_sources` skips them (they run only in the
user-launched residual harness).

Template (copy this shape in every source module)::

    from tests.sources._base import register, http_probe, fields_from_csv, ProbeContext
    from tests.stress import classify
    from tests.stress.http_client import build_client
    from tests.stress.metrics import TestResult

    @register(
        test_id="current-eccc-datamart-on",
        category="current",
        source_id="SRC-ECCC-DATAMART",
        label="ECCC Datamart bulk hourly CSV (ON)",
        jurisdiction="ON",
        licence="OGL-Canada / ECCC End-use Licence v2.1.1",
        commercial_ok="yes",
    )
    async def probe(spec, ctx: ProbeContext) -> TestResult:
        url = "https://dd.weather.gc.ca/today/hydrometric/csv/ON/hourly/ON_hourly_hydrometric.csv"
        recs = []
        async with build_client(timeout=ctx.request_timeout) as client:
            f = await http_probe(ctx, client, url, source_id=spec.source_id, category=spec.category)
            recs.append(f.record)
            if f.ok:
                fields = fields_from_csv(f.text)
                f.record.records_parsed = max(0, f.text.count("\\n") - 1)
                return spec.result(retrievable=True, reason_category=classify.OK,
                                   endpoint=url, fields_found=fields,
                                   record_count=f.record.records_parsed,
                                   latency_ms=f.record.latency_ms,
                                   sample=f.text[:800], requests=recs)
        return spec.result(retrievable=False, reason_category=f.record.reason_category,
                           reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx

from tests.stress import classify
from tests.stress.http_client import build_client  # re-export for convenience
from tests.stress.metrics import RequestRecord, ResultLog, TestResult, utcnow_iso

# ── Registry ────────────────────────────────────────────────────────
REGISTRY: list["ProbeSpec"] = []


@dataclass
class ProbeContext:
    """Runtime context handed to every probe."""
    log: ResultLog
    run_id: str
    sample_size: int = 3          # stations/records to sample where applicable
    request_timeout: float = 60.0
    cache_dir: str = "/tmp/wp-ds-cache"   # for HYDAT SQLite / large downloads
    allow_downloads: bool = True  # gate multi-MB downloads (HYDAT, CanSWE)


@dataclass
class ProbeSpec:
    test_id: str
    category: str
    source_id: str
    label: str
    jurisdiction: str
    licence: str
    commercial_ok: str
    sanctioned: bool
    fn: Callable[["ProbeSpec", ProbeContext], Awaitable[TestResult]]

    def result(self, *, retrievable: bool, reason_category: str, **kw) -> TestResult:
        """Build a TestResult with this spec's metadata pre-filled."""
        return TestResult(
            test_id=self.test_id, category=self.category, source_id=self.source_id,
            label=self.label, jurisdiction=self.jurisdiction, licence=self.licence,
            commercial_ok=self.commercial_ok, retrievable=retrievable,
            reason_category=reason_category, **kw,
        )


def register(*, test_id, category, source_id, label, jurisdiction,
             licence, commercial_ok, sanctioned: bool = True):
    """Decorator registering an `async def fn(spec, ctx) -> TestResult`."""
    def deco(fn):
        REGISTRY.append(ProbeSpec(
            test_id=test_id, category=category, source_id=source_id, label=label,
            jurisdiction=jurisdiction, licence=licence, commercial_ok=commercial_ok,
            sanctioned=sanctioned, fn=fn,
        ))
        return fn
    return deco


# ── HTTP helper ─────────────────────────────────────────────────────
@dataclass
class Fetch:
    record: RequestRecord
    response: httpx.Response | None
    ok: bool
    text: str = ""

    def json(self):
        if self.response is None:
            return None
        return self.response.json()


def _retry_after(resp: httpx.Response | None) -> float | None:
    if resp is None:
        return None
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    try:
        return float(ra)
    except ValueError:
        return None  # HTTP-date form; not parsed here


async def http_probe(
    ctx: ProbeContext,
    client: httpx.AsyncClient,
    url: str,
    *,
    source_id: str,
    category: str,
    method: str = "GET",
    params: dict | None = None,
    headers: dict | None = None,
    from_metadata: bool = False,
    read_text: bool = True,
    notes: str = "",
) -> Fetch:
    """Perform one HTTP attempt; time + classify it; return a Fetch.

    Never raises for HTTP/transport errors — classifies them into a
    RequestRecord so the caller can decide. `from_metadata=True` marks URLs
    the upstream advertised (so a 404 is an upstream gap, not our bug).
    """
    t0 = time.perf_counter()
    resp: httpx.Response | None = None
    status: int | None = None
    resp_bytes = 0
    text = ""
    error_type = ""
    try:
        resp = await client.request(method, url, params=params, headers=headers)
        status = resp.status_code
        resp_bytes = len(resp.content)
        if read_text:
            try:
                text = resp.text
            except Exception:  # decoding issue
                text = ""
        reason = classify.classify_status(status, from_metadata=from_metadata)
        outcome = "success" if reason == classify.OK else "failure"
        reason_detail = "" if outcome == "success" else f"HTTP {status}"
    except BaseException as exc:  # transport/parse
        reason, reason_detail = classify.classify_exception(exc)
        outcome = "failure"
        error_type = type(exc).__name__

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    rec = RequestRecord(
        ts_utc=utcnow_iso(), source_id=source_id, category=category, method=method,
        url=url, http_status=status, outcome=outcome, reason_category=reason,
        reason_detail=reason_detail, error_type=error_type, latency_ms=latency_ms,
        resp_bytes=resp_bytes, records_parsed=0, retry_after_s=_retry_after(resp),
        notes=notes,
    )
    ok = outcome == "success"
    return Fetch(record=rec, response=resp, ok=ok, text=text)


# ── Field-inventory helpers ─────────────────────────────────────────
def fields_from_csv(text: str, delimiter: str = ",", header_row: int = 0) -> list[str]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) <= header_row:
        return []
    return [h.strip().strip('"') for h in lines[header_row].split(delimiter)]


def fields_from_json(obj) -> list[str]:
    """Best-effort field discovery for dict / list-of-dict / GeoJSON."""
    if isinstance(obj, dict):
        if "features" in obj and isinstance(obj["features"], list) and obj["features"]:
            feat = obj["features"][0]
            props = feat.get("properties", {}) if isinstance(feat, dict) else {}
            keys = list(props.keys())
            if isinstance(feat, dict) and "geometry" in feat:
                keys.append("geometry")
            return keys
        if "value" in obj and isinstance(obj["value"], list) and obj["value"]:
            first = obj["value"][0]
            return list(first.keys()) if isinstance(first, dict) else []
        return list(obj.keys())
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return list(obj[0].keys())
    return []


def year_span(years) -> tuple[int | None, int | None, int | None]:
    ys = [int(y) for y in years if y is not None and str(y).strip() != ""]
    if not ys:
        return None, None, None
    lo, hi = min(ys), max(ys)
    return lo, hi, (hi - lo + 1)
