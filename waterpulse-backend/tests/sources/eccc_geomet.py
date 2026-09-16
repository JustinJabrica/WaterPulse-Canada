"""
ECCC MSC GeoMet — OGC API - Features (api.weather.gc.ca).

The sanctioned, structured, query-per-station/province JSON+GeoJSON front door
to Water Survey of Canada hydrometry. Same authority as the Datamart bulk CSV
and the HYDAT SQLite archive, but delivered as a filterable OGC API - Features
service (bbox / property filters / paging) so you can pull exactly the stations,
the current readings, or the historical series you need without downloading a
whole file. Reference template for a paged OGC-API GeoJSON probe.

Collections probed:
  - hydrometric-stations          — station inventory (per province/territory)
  - hydrometric-realtime          — current level/discharge observations
  - hydrometric-daily-mean        — daily mean flow/level (full record)
  - hydrometric-monthly-mean      — monthly mean flow/level
  - hydrometric-annual-statistics — annual max/min statistics
  - hydrometric-annual-peaks      — annual instantaneous peaks

Endpoints (OGC API - Features items):
  https://api.weather.gc.ca/collections/<collection>/items?f=json&...
  Common query params: limit, PROV_TERR_STATE_LOC, STATION_NUMBER, bbox, datetime.
  Responses are GeoJSON FeatureCollections carrying `numberMatched`/`numberReturned`.

Licence: OGL-Canada / ECCC MSC Data Servers End-use Licence v2.1.1 (commercial OK,
attribution "Data Source: Environment and Climate Change Canada").
Citation / docs: https://api.weather.gc.ca/  (see also
https://eccc-msc.github.io/open-data/msc-geomet/readme_en/ )
Policy: low-load, read-only; MSC asks to contact them only above ~1 req/s sustained.
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext,
    fields_from_json,
    http_probe,
    register,
    year_span,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

GEOMET = "https://api.weather.gc.ca/collections"
STATIONS_URL = f"{GEOMET}/hydrometric-stations/items"
REALTIME_URL = f"{GEOMET}/hydrometric-realtime/items"

SAMPLE_STATION = "05BB001"  # Bow River at Banff — long, dense record for depth probing
PROVINCES = ["AB", "BC", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "YT", "NT", "NU"]

LICENCE = "OGL-Canada / ECCC MSC End-use Licence v2.1.1"

# Historical collections + a human blurb, probed one sample station each.
HISTORICAL_COLLECTIONS = [
    ("hydrometric-daily-mean", "daily mean flow/level (full period of record)"),
    ("hydrometric-monthly-mean", "monthly mean flow/level"),
    ("hydrometric-annual-statistics", "annual max/min statistics"),
    ("hydrometric-annual-peaks", "annual instantaneous peaks"),
]


# ── helpers ─────────────────────────────────────────────────────────
def _features(data) -> list:
    if isinstance(data, dict) and isinstance(data.get("features"), list):
        return data["features"]
    return []


def _number_matched(data):
    if isinstance(data, dict):
        nm = data.get("numberMatched")
        if isinstance(nm, int):
            return nm
    return None


def _distinct_stations(feats) -> int | None:
    ids = set()
    for ft in feats:
        if not isinstance(ft, dict):
            continue
        props = ft.get("properties") or {}
        sid = props.get("STATION_NUMBER")
        if sid:
            ids.add(sid)
    return len(ids) if ids else None


def _years_from_features(feats) -> list[int]:
    """Pull a 4-digit year from each feature's DATE (ISO YYYY-MM-DD) or YEAR
    property — covers daily/monthly (DATE) and annual (YEAR/DATE) collections."""
    years: list[int] = []
    for ft in feats:
        if not isinstance(ft, dict):
            continue
        props = ft.get("properties") or {}
        val = (
            props.get("DATE")
            or props.get("YEAR")
            or props.get("MAX_DATE")
            or props.get("MIN_DATE")
        )
        if val is None:
            continue
        s = str(val).strip()
        if len(s) >= 4 and s[:4].isdigit():
            years.append(int(s[:4]))
    return years


# ── (a) STATIONS — per province/territory ───────────────────────────
async def _probe_stations(spec, ctx: ProbeContext) -> TestResult:
    url = STATIONS_URL
    params = {"f": "json", "limit": 10, "PROV_TERR_STATE_LOC": spec.jurisdiction}
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, url, source_id=spec.source_id, category=spec.category,
            params=params, from_metadata=False,
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
        except Exception as exc:  # noqa: BLE001 — parse guard, keep run alive
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs,
            )
        feats = _features(data)
        fields = fields_from_json(data)
        number_matched = _number_matched(data)
        f.record.records_parsed = len(feats)
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(feats), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(feats),
            station_count=number_matched, latency_ms=f.record.latency_ms,
            sample=f.text[:800], requests=recs,
            notes=f"OGC API stations inventory for {spec.jurisdiction} "
                  f"(limit=10; numberMatched={number_matched})",
            extra={"number_matched": number_matched, "collection": "hydrometric-stations"},
        )


for _prov in PROVINCES:
    register(
        test_id=f"stations-eccc-geomet-{_prov.lower()}",
        category="stations",
        source_id="SRC-ECCC-GEOMET",
        label=f"ECCC GeoMet OGC API hydrometric stations ({_prov})",
        jurisdiction=_prov,
        licence=LICENCE,
        commercial_ok="yes",
    )(_probe_stations)


# ── (b) CURRENT — one national realtime sample ──────────────────────
async def _probe_current(spec, ctx: ProbeContext) -> TestResult:
    url = REALTIME_URL
    params = {"f": "json", "limit": 10}
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, url, source_id=spec.source_id, category=spec.category,
            params=params, from_metadata=False,
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs,
            )
        feats = _features(data)
        fields = fields_from_json(data)
        number_matched = _number_matched(data)
        f.record.records_parsed = len(feats)
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(feats), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(feats),
            station_count=_distinct_stations(feats), latency_ms=f.record.latency_ms,
            sample=f.text[:800], requests=recs,
            notes=f"national realtime observations sample (limit=10; "
                  f"numberMatched={number_matched})",
            extra={"number_matched": number_matched, "collection": "hydrometric-realtime"},
        )


register(
    test_id="current-eccc-geomet-ca",
    category="current",
    source_id="SRC-ECCC-GEOMET",
    label="ECCC GeoMet OGC API hydrometric realtime (national sample)",
    jurisdiction="CA",
    licence=LICENCE,
    commercial_ok="yes",
)(_probe_current)


# ── (c) HISTORICAL — 4 collections, one sample station each ─────────
def _make_historical(collection: str, blurb: str):
    async def _probe(spec, ctx: ProbeContext) -> TestResult:
        url = f"{GEOMET}/{collection}/items"
        params = {"f": "json", "limit": 50, "STATION_NUMBER": SAMPLE_STATION}
        recs = []
        async with build_client(timeout=ctx.request_timeout) as client:
            f = await http_probe(
                ctx, client, url, source_id=spec.source_id, category=spec.category,
                params=params, from_metadata=False,
            )
            recs.append(f.record)
            if not f.ok:
                return spec.result(
                    retrievable=False, reason_category=f.record.reason_category,
                    reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                )
            try:
                data = f.json()
            except Exception as exc:  # noqa: BLE001
                _, detail = classify.classify_exception(exc)
                return spec.result(
                    retrievable=False, reason_category=classify.PARSE_ERROR,
                    reason_detail=detail, endpoint=url, sample=f.text[:800],
                    requests=recs,
                )
            feats = _features(data)
            fields = fields_from_json(data)
            number_matched = _number_matched(data)
            lo, hi, span = year_span(_years_from_features(feats))
            f.record.records_parsed = len(feats)
            reason = classify.OK if feats else classify.OK_EMPTY
            return spec.result(
                retrievable=bool(feats), reason_category=reason, endpoint=url,
                fields_found=fields, record_count=len(feats),
                station_count=_distinct_stations(feats),
                earliest_year=lo, latest_year=hi, span_years=span,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes=f"{blurb}; sample station {SAMPLE_STATION} "
                      f"(limit=50; numberMatched={number_matched})",
                extra={"number_matched": number_matched, "collection": collection,
                       "sample_station": SAMPLE_STATION},
            )

    return _probe


for _coll, _blurb in HISTORICAL_COLLECTIONS:
    _suffix = _coll.replace("hydrometric-", "")
    register(
        test_id=f"historical-eccc-geomet-{_suffix}",
        category="historical",
        source_id="SRC-ECCC-GEOMET",
        label=f"ECCC GeoMet OGC API {_coll} ({SAMPLE_STATION} sample)",
        jurisdiction="CA",
        licence=LICENCE,
        commercial_ok="yes",
    )(_make_historical(_coll, _blurb))
