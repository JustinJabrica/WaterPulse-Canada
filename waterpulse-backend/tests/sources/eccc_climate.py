"""
ECCC observed climate — GeoMet OGC API (api.weather.gc.ca).

Environment and Climate Change Canada's adjusted/observed climate station
records, served as OGC API - Features collections. These carry the observed
precipitation and snow-on-ground fields (TOTAL_PRECIPITATION, SNOW_ON_GROUND)
alongside temperature, for the full station period of record (some series
reach the early 1900s). The RDPA/CaPA collection provides gridded precip
accumulation analysis; here we only read its collection metadata (never the
coverage grid).

Endpoints (all under https://api.weather.gc.ca):
  - collections/climate-daily/items?f=json&limit=10    daily obs (precip, snow)
  - collections/climate-hourly/items?f=json&limit=10   hourly obs
  - collections/climate-monthly/items?f=json&limit=10  monthly summaries
  - collections/climate-stations/items?f=json&limit=5  station metadata
  - collections/weather:rdpa:10km:6f?f=json            RDPA gridded (metadata only)

Licence: Open Government Licence - Canada (OGL-Canada); commercial use OK with
attribution "Data Source: Environment and Climate Change Canada".
Citation / docs: https://api.weather.gc.ca/ ;
https://eccc-msc.github.io/open-data/msc-geomet/readme_en/
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

BASE = "https://api.weather.gc.ca"
LICENCE = "OGL-Canada"
SRC = "SRC-ECCC-CLIMATE"

# Precip / snow field names advertised by the climate collections.
PRECIP_FIELDS = ("TOTAL_PRECIPITATION", "TOTAL_RAIN", "TOTAL_SNOW", "PRECIPITATION")
SNOW_FIELDS = ("SNOW_ON_GROUND",)

# Keys we harvest a 4-digit year from, to estimate historical depth from a sample.
_YEAR_KEYS = (
    "LOCAL_YEAR",
    "LOCAL_DATE",
    "FIRST_DATE",
    "LAST_DATE",
    "DLY_FIRST_DATE",
    "DLY_LAST_DATE",
    "FIRST_YEAR",
    "LAST_YEAR",
)

# test_id -> per-collection config for the shared OGC items probe.
ITEMS = {
    "precip-eccc-climate-daily": {
        "collection": "climate-daily",
        "limit": 10,
        "category": "precip",
        "label": "ECCC GeoMet climate-daily (daily obs: precip + snow-on-ground)",
    },
    "precip-eccc-climate-hourly": {
        "collection": "climate-hourly",
        "limit": 10,
        "category": "precip",
        "label": "ECCC GeoMet climate-hourly (hourly obs)",
    },
    "precip-eccc-climate-monthly": {
        "collection": "climate-monthly",
        "limit": 10,
        "category": "precip",
        "label": "ECCC GeoMet climate-monthly (monthly summaries)",
    },
    "stations-eccc-climate-stations": {
        "collection": "climate-stations",
        "limit": 5,
        "category": "stations",
        "label": "ECCC GeoMet climate-stations (station metadata)",
    },
}


def _years_from_features(features: list) -> list:
    """Best-effort 4-digit year harvest across a small sample of features."""
    years: list[int] = []
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties", {}) or {}
        for key in _YEAR_KEYS:
            val = props.get(key)
            if val is None:
                continue
            s = str(val).strip()
            if len(s) >= 4 and s[:4].isdigit():
                yr = int(s[:4])
                if 1800 <= yr <= 2100:
                    years.append(yr)
    return years


async def _probe_items(spec, ctx: ProbeContext) -> TestResult:
    cfg = ITEMS[spec.test_id]
    coll = cfg["collection"]
    limit = cfg["limit"]
    url = f"{BASE}/collections/{coll}/items"
    params = {"f": "json", "limit": limit}
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
            fields = fields_from_json(data)
        except Exception as exc:  # bytes returned but unparseable
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs,
            )

        features = data.get("features", []) if isinstance(data, dict) else []
        f.record.records_parsed = len(features)
        number_matched = data.get("numberMatched") if isinstance(data, dict) else None
        record_count = number_matched if isinstance(number_matched, int) else len(features)
        station_count = (
            number_matched if coll == "climate-stations" and isinstance(number_matched, int)
            else None
        )

        years = _years_from_features(features)
        lo, hi, span = year_span(years)

        has_precip = any(x in fields for x in PRECIP_FIELDS)
        has_snow = any(x in fields for x in SNOW_FIELDS)
        reason = classify.OK if (fields and features) else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(features),
            reason_category=reason,
            endpoint=url,
            fields_found=fields,
            record_count=record_count,
            station_count=station_count,
            earliest_year=lo,
            latest_year=hi,
            span_years=span,
            latency_ms=f.record.latency_ms,
            sample=f.text[:800],
            requests=recs,
            notes=(
                f"{coll}: precip_field={has_precip} snow_on_ground={has_snow}; "
                f"sample year-range from limit={limit}"
            ),
            extra={
                "collection": coll,
                "number_matched": number_matched,
                "has_precip": has_precip,
                "has_snow_on_ground": has_snow,
                "precip_fields_present": [x for x in PRECIP_FIELDS if x in fields],
            },
        )


async def _probe_rdpa(spec, ctx: ProbeContext) -> TestResult:
    """RDPA/CaPA gridded precip accumulation — collection METADATA only.

    We deliberately do NOT fetch the coverage grid (large binary); we read the
    OGC collection description and report its top-level keys as fields.
    """
    url = f"{BASE}/collections/weather:rdpa:10km:6f"
    params = {"f": "json"}
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, url, source_id=spec.source_id, category=spec.category,
            params=params, from_metadata=True,
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
            fields = fields_from_json(data)  # collection metadata -> top-level keys
        except Exception as exc:
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs,
            )
        title = data.get("title") if isinstance(data, dict) else None
        coll_id = data.get("id") if isinstance(data, dict) else None
        return spec.result(
            retrievable=bool(fields),
            reason_category=classify.OK if fields else classify.OK_EMPTY,
            endpoint=url,
            fields_found=fields,
            latency_ms=f.record.latency_ms,
            sample=f.text[:800],
            requests=recs,
            notes=(
                "RDPA/CaPA gridded precip accumulation; collection metadata only "
                "(coverage grid NOT fetched)"
            ),
            extra={"collection": coll_id or "weather:rdpa:10km:6f", "title": title},
        )


# ── Register the four OGC items probes + the RDPA metadata probe ────────
for _tid, _cfg in ITEMS.items():
    register(
        test_id=_tid,
        category=_cfg["category"],
        source_id=SRC,
        label=_cfg["label"],
        jurisdiction="CA",
        licence=LICENCE,
        commercial_ok="yes",
    )(_probe_items)

register(
    test_id="precip-eccc-rdpa-capa-10km",
    category="precip",
    source_id=SRC,
    label="ECCC GeoMet RDPA/CaPA 10km 6h precip accumulation (collection metadata)",
    jurisdiction="CA",
    licence=LICENCE,
    commercial_ok="yes",
)(_probe_rdpa)
