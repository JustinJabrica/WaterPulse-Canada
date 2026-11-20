"""
Density-adding weather networks (category="weather").

Beyond the core ECCC hourly stations, two sources add real observing density
nationwide and are cleanly fetchable:

(a) SRC-ECCC-SWOB — ECCC Surface Weather / Observation (SWOB) partner network,
    served as OGC-API-Features GeoJSON on api.weather.gc.ca. The `swob-realtime`
    collection carries partner + MSC station observations beyond the core hourly
    set. Licence: OGL-Canada (commercial OK).
    https://api.weather.gc.ca/collections/swob-realtime

(b) SRC-AWC-METAR — aviation METAR observations for Canadian aerodromes (CYxx)
    via the US Aviation Weather Center JSON API. Public domain, no key, ~190
    Canadian sites, point-queryable by ICAO id. (Same underlying obs as NAV
    CANADA, far easier to fetch.)
    https://aviationweather.gov/data/api/
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext, fields_from_json, http_probe, latest_ts_from_features, register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

SWOB_ITEMS = "https://api.weather.gc.ca/collections/swob-realtime/items"
METAR_URL = "https://aviationweather.gov/api/data/metar"


@register(
    test_id="weather-eccc-swob-ca",
    category="weather",
    source_id="SRC-ECCC-SWOB",
    label="ECCC SWOB partner weather-station observations (OGC API)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC MSC End-use Licence",
    commercial_ok="yes",
)
async def probe_swob(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"f": "json", "limit": 10}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, SWOB_ITEMS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes="SWOB-realtime OGC items sample (partner + MSC stations)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=SWOB_ITEMS, requests=recs,
            )
        try:
            data = f.json()
            feats = data.get("features", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
            number_matched = data.get("numberMatched") if isinstance(data, dict) else None
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=SWOB_ITEMS, sample=f.text[:800], requests=recs,
            )
        latest_obs, age_min = latest_ts_from_features(feats)
        f.record.records_parsed = len(feats)
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(feats), reason_category=reason, endpoint=SWOB_ITEMS,
            fields_found=fields, record_count=len(feats), station_count=number_matched,
            latency_ms=f.record.latency_ms, latest_obs_utc=latest_obs, data_age_minutes=age_min,
            sample=f.text[:800], requests=recs,
            notes=f"partner-network density beyond core MSC hourly (numberMatched={number_matched}); "
                  "SWOB-ML element codes",
            extra={"number_matched": number_matched},
        )


@register(
    test_id="weather-awc-metar-ca",
    category="weather",
    source_id="SRC-AWC-METAR",
    label="Aviation METAR observations, Canadian aerodromes (CYxx)",
    jurisdiction="CA",
    licence="US Government public domain",
    commercial_ok="yes",
)
async def probe_metar(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"ids": "CYYZ,CYVR,CYUL,CYYC,CYOW", "format": "json"}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, METAR_URL, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes="METAR JSON for a few Canadian aerodromes",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=METAR_URL, requests=recs,
            )
        try:
            data = f.json()
            rows = data if isinstance(data, list) else []
            fields = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
            times = [r.get("reportTime") for r in rows if isinstance(r, dict)]
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=METAR_URL, sample=f.text[:800], requests=recs,
            )
        from tests.sources._base import freshness_from
        latest_obs, age_min = freshness_from(times)
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=METAR_URL,
            fields_found=fields, record_count=len(rows),
            latency_ms=f.record.latency_ms, latest_obs_utc=latest_obs, data_age_minutes=age_min,
            sample=f.text[:800], requests=recs,
            notes="~190 Canadian CYxx aerodromes available; query by ICAO id or bbox",
            extra={"sample_ids": params["ids"]},
        )
