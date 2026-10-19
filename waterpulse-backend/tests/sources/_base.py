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

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    retries: int = 2,
    retry_backoff: float = 1.5,
) -> Fetch:
    """Perform an HTTP attempt (with bounded retry on TRANSIENT failures);
    time + classify it; return a Fetch.

    Never raises for HTTP/transport errors — classifies them into a
    RequestRecord so the caller can decide. `from_metadata=True` marks URLs
    the upstream advertised (so a 404 is an upstream gap, not our bug).

    Transient reasons (5xx, 429, connect/read timeouts) are retried up to
    `retries` times with linear backoff, honouring `Retry-After` — this makes
    the sanctioned suite deterministic against upstream blips (e.g. GeoMet's
    occasional 500s). NON-transient outcomes (2xx, 4xx, connect_refused,
    dns_error, parse) return immediately. The residual harness passes
    `retries=0` so its throttle/refusal signals stay pristine.
    """
    attempt = 0
    while True:
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
        ra = _retry_after(resp)
        transient = reason in (classify.HTTP_5XX, classify.HTTP_429,
                               classify.CONNECT_TIMEOUT, classify.READ_TIMEOUT)
        will_retry = outcome != "success" and transient and attempt < retries
        note = notes
        if attempt:
            note = (f"{notes} [attempt {attempt + 1}]").strip()

        rec = RequestRecord(
            ts_utc=utcnow_iso(), source_id=source_id, category=category, method=method,
            url=url, http_status=status, outcome=outcome, reason_category=reason,
            reason_detail=reason_detail, error_type=error_type, latency_ms=latency_ms,
            resp_bytes=resp_bytes, records_parsed=0, retry_after_s=ra, notes=note,
        )
        if not will_retry:
            return Fetch(record=rec, response=resp, ok=(outcome == "success"), text=text)
        await asyncio.sleep(min(ra if ra else retry_backoff * (attempt + 1), 15.0))
        attempt += 1


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


# ── Freshness helpers (data age of real-time sources) ───────────────
# Used to populate TestResult.latest_obs_utc / data_age_minutes so source
# prioritization can rank by how fresh each feed's latest reading is.
_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?")


def parse_ts(value) -> datetime | None:
    """Parse an ISO-ish timestamp to a tz-aware UTC datetime. Accepts a trailing
    'Z', numeric offsets, 'T' or space separators, and date-only strings; returns
    None if unparseable. Naive timestamps are assumed UTC."""
    if value is None:
        return None
    s0 = str(value).strip().strip('"')
    if not s0:
        return None
    s = s0.replace("Z", "+00:00")
    for cand in (s, s.replace(" ", "T", 1)):
        try:
            dt = datetime.fromisoformat(cand)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None \
                else dt.astimezone(timezone.utc)
        except ValueError:
            continue
    # Non-ISO government formats (e.g. NL ADRS "10/12/2026 7:55:21 AM"). North
    # American m/d/Y is assumed; naive values are treated as UTC (a few hours'
    # tz error is immaterial to a freshness-ranking signal).
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M",
                "%Y/%m/%d %H:%M:%S", "%d-%b-%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(s0, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    m = _TS_RE.search(s)
    if m:
        try:
            return datetime.fromisoformat(m.group(0).replace(" ", "T", 1)) \
                .replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def freshness_from(timestamps, now: datetime | None = None,
                   future_tol_min: float = 180.0) -> tuple[str, float | None]:
    """From an iterable of timestamp strings/datetimes, return
    (latest_obs_utc_iso, data_age_minutes) for the most recent OBSERVATION — the
    max timestamp no more than `future_tol_min` minutes ahead of now (so forecast
    rows are ignored). Returns ("", None) if nothing parses."""
    now = now or datetime.now(timezone.utc)
    cutoff = now.timestamp() + future_tol_min * 60
    best: datetime | None = None
    for t in timestamps:
        dt = t if isinstance(t, datetime) else parse_ts(t)
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt.timestamp() > cutoff:
            continue  # future/forecast timestamp — not an observation
        if best is None or dt > best:
            best = dt
    if best is None:
        return "", None
    return best.isoformat(timespec="seconds"), round((now - best).total_seconds() / 60.0, 1)


def latest_ts_from_csv(text: str, prefer_cols: tuple = (), delimiter: str = ",",
                       max_scan: int = 4000) -> tuple[str, float | None]:
    """Freshest observation timestamp in a CSV. Uses columns named in
    `prefer_cols` (case-insensitive) when present, else scans every cell. Scans
    at most `max_scan` rows (head+tail sample) so multi-million-row bundles stay
    fast. Returns (latest_obs_utc_iso, data_age_minutes)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return "", None
    header = [h.strip().strip('"') for h in lines[0].split(delimiter)]
    hlow = [h.lower() for h in header]
    idxs = [hlow.index(c.lower()) for c in prefer_cols if c.lower() in hlow]
    rows = lines[1:]
    if len(rows) > max_scan:
        half = max_scan // 2
        rows = rows[:half] + rows[-half:]
    ts: list = []
    for ln in rows:
        cells = ln.split(delimiter)
        if idxs:
            ts.extend(cells[i].strip().strip('"') for i in idxs if i < len(cells))
        else:
            ts.extend(c.strip().strip('"') for c in cells)
    return freshness_from(ts)


def latest_ts_from_features(features, prefer_keys: tuple = ()) -> tuple[str, float | None]:
    """Freshest observation timestamp across GeoJSON feature properties. Uses
    `prefer_keys` when present, else scans all string property values. Returns
    (latest_obs_utc_iso, data_age_minutes)."""
    ts: list = []
    for ft in features or []:
        props = ft.get("properties", {}) if isinstance(ft, dict) else {}
        if not isinstance(props, dict):
            continue
        if prefer_keys:
            ts.extend(props[k] for k in prefer_keys if props.get(k) is not None)
        else:
            ts.extend(v for v in props.values() if isinstance(v, str))
    return freshness_from(ts)
