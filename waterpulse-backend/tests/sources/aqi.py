"""
Air Quality (AQI) sources.

Two sanctioned, read-only public APIs for the app's air-quality layer:

(a) ECCC AQHI — the Air Quality Health Index observations feed from MSC GeoMet's
    OGC API (api.weather.gc.ca). AQHI is a Canadian 1-10+ index (NOT US-EPA AQI):
    1-3 Low risk, 4-6 Moderate, 7-10 High, >10 Very High. GeoJSON items feed.
      Endpoint: https://api.weather.gc.ca/collections/aqhi-observations-realtime/items?f=json&limit=10
      Licence:  OGL-Canada / MSC GeoMet End-use Licence (commercial OK, attribution
                "Data Source: Environment and Climate Change Canada").
      Citation: https://api.weather.gc.ca/  (collections/aqhi-observations-realtime)

(b) Open-Meteo Air Quality — free forecast/analysis API exposing US-EPA us_aqi
    (0-500) plus pm2_5 / pm10 concentrations. This is the scale the app renders.
      Endpoint: https://air-quality-api.open-meteo.com/v1/air-quality
      Params:   latitude, longitude, current=us_aqi,pm2_5,pm10
      Licence:  CC-BY-4.0 (attribution "Weather data by Open-Meteo.com"); free tier
                is non-commercial use only.
      Citation: https://open-meteo.com/en/docs/air-quality-api

SCALE (recorded in notes/extra for BOTH): the app uses us_aqi 0-500 + pm2_5/pm10
(US-EPA) from Open-Meteo; ECCC AQHI is a separate 1-10 index and is NOT the same
scale as US AQI.
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext,
    fields_from_json,
    http_probe,
    register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── Shared scale note (both sources describe air quality on different scales) ──
_SCALE = (
    "app uses us_aqi 0-500 + pm2_5/pm10 (US-EPA) from Open-Meteo; "
    "ECCC AQHI is a 1-10 health index, NOT US AQI"
)
_SCALE_EXTRA = {
    "app_scale": "us_aqi 0-500 + pm2_5/pm10 (US-EPA)",
    "aqhi_scale": "1-10 index (1-3 low, 4-6 moderate, 7-10 high, >10 very high)",
}


# ── (a) ECCC AQHI observations (OGC API GeoJSON) ─────────────────────
AQHI_URL = "https://api.weather.gc.ca/collections/aqhi-observations-realtime/items"


async def _probe_eccc_aqhi(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"f": "json", "limit": 10}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, AQHI_URL, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes="AQHI observations OGC items (limit=10)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=AQHI_URL, requests=recs,
            )
        try:
            data = f.json()
            fields = fields_from_json(data)
            feats = data.get("features", []) if isinstance(data, dict) else []
            n_returned = len(feats)
            # OGC APIs advertise total match count; fall back to page size.
            total = data.get("numberMatched") if isinstance(data, dict) else None
            record_count = total if isinstance(total, int) else n_returned
            # distinct AQHI stations in this page (property name varies)
            stations = set()
            for feat in feats:
                if not isinstance(feat, dict):
                    continue
                props = feat.get("properties", {}) or {}
                sid = props.get("id") or props.get("aqhi_station") or props.get("location_id")
                if sid is not None:
                    stations.add(sid)
        except Exception as exc:  # unexpected shape → parse error, keep run alive
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=AQHI_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = n_returned
        return spec.result(
            retrievable=bool(fields or n_returned),
            reason_category=classify.OK if (fields or n_returned) else classify.OK_EMPTY,
            endpoint=AQHI_URL, fields_found=fields, record_count=record_count,
            station_count=len(stations) or None,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=f"AQHI 1-10 index (NOT US AQI). {_SCALE}",
            extra={**_SCALE_EXTRA, "number_returned": n_returned, "note": "realtime, no history depth"},
        )


register(
    test_id="aqi-eccc-aqhi-ca",
    category="aqi",
    source_id="SRC-ECCC-AQHI",
    label="ECCC AQHI observations (GeoMet OGC API)",
    jurisdiction="CA",
    licence="OGL-Canada / MSC GeoMet End-use Licence",
    commercial_ok="yes",
    sanctioned=True,
)(_probe_eccc_aqhi)


# ── (b) Open-Meteo Air Quality (US-EPA us_aqi + pm2_5/pm10) ──────────
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def _probe_open_meteo_aqi(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {
        "latitude": 51.05,
        "longitude": -114.07,   # Calgary, AB (sample point)
        "current": "us_aqi,pm2_5,pm10",
    }
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, OPEN_METEO_URL, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes="us_aqi,pm2_5,pm10 @ 51.05,-114.07",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=OPEN_METEO_URL, requests=recs,
            )
        try:
            data = f.json()
            current = data.get("current", {}) if isinstance(data, dict) else {}
            fields = list(current.keys()) if isinstance(current, dict) else []
            has_value = bool(current) and any(
                k != "time" and current.get(k) is not None for k in current
            )
        except Exception as exc:  # unexpected shape → parse error, keep run alive
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=OPEN_METEO_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = 1 if has_value else 0
        return spec.result(
            retrievable=bool(fields),
            reason_category=classify.OK if has_value else classify.OK_EMPTY,
            endpoint=OPEN_METEO_URL, fields_found=fields,
            record_count=1 if has_value else 0, station_count=None,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=f"single-point current AQI. {_SCALE}",
            extra={**_SCALE_EXTRA, "sample_point": "51.05,-114.07 (Calgary)",
                   "requested_current": "us_aqi,pm2_5,pm10"},
        )


register(
    test_id="aqi-open-meteo-aqi",
    category="aqi",
    source_id="SRC-OPEN-METEO-AQI",
    label="Open-Meteo Air Quality (us_aqi + pm2_5/pm10)",
    jurisdiction="multi",
    licence="CC-BY-4.0",
    commercial_ok="non-commercial",
    sanctioned=True,
)(_probe_open_meteo_aqi)
