"""
MET Norway — Locationforecast 2.0 (api.met.no) point weather forecast.

The Norwegian Meteorological Institute's free global forecast API. The
`compact` variant returns a GeoJSON Feature whose `properties.timeseries[]`
holds an hourly-then-6-hourly forecast (~10 days). Each timestep carries an
`instant.details` block (temperature, humidity, wind, cloud, pressure) plus
`next_1_hours` / `next_6_hours` / `next_12_hours` blocks with a symbol code and
precipitation amount. Reference probe for the "weather" category (forecast /
point query rather than a station feed).

Endpoint (probed): GET
  https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=<>&lon=<>
Sibling `.../complete` adds wind_speed_of_gust, ultraviolet_index_clear_sky,
dew_point_temperature, fog/cloud-layer fractions and (in the next_X details)
probability_of_precipitation — several of the APP-required fields the compact
endpoint omits.

Licence: CC BY 4.0 + NLOD 2.0 (Norwegian Licence for Open Government Data);
commercial use permitted with attribution ("Data from MET Norway").
Terms of service: https://api.met.no/doc/TermsOfService  (a descriptive
User-Agent identifying the application is REQUIRED — build_client already sends
ours; a missing/default UA gets a 403). Throttle: <20 req/s; honour the
Expires header for caching.
Citation: https://api.met.no/weatherapi/locationforecast/2.0/documentation
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

BASE = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
# Calgary, AB — representative Canadian point query.
PARAMS = {"lat": 51.05, "lon": -114.07}

# Fields the WaterPulse app UI wants on a forecast card, and how MET Norway
# exposes (or omits) each. Presence is re-checked against the live response.
APP_REQUIRED = (
    "apparent_temperature",       # "feels like" — NOT provided by MET Norway
    "uv_index",                   # only ultraviolet_index_clear_sky on /complete
    "visibility",                 # NOT provided by MET Norway locationforecast
    "wind_gusts",                 # wind_speed_of_gust only on /complete
    "precipitation_probability",  # probability_of_precipitation only on /complete
    "is_day",                     # derivable from symbol_code _day/_night suffix
)


@register(
    test_id="weather-met-norway-locationforecast",
    category="weather",
    source_id="SRC-MET-NORWAY",
    label="MET Norway Locationforecast 2.0 (compact point forecast)",
    jurisdiction="CA",
    licence="CC-BY 4.0 / NLOD 2.0",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_met_norway(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, BASE, source_id=spec.source_id, category=spec.category,
            params=PARAMS, from_metadata=False,
            notes="locationforecast 2.0 compact (lat/lon point)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=BASE, requests=recs,
            )

        try:
            data = f.json()
            props = (data or {}).get("properties", {})
            ts = props.get("timeseries", []) or []
            if not ts:
                return spec.result(
                    retrievable=True, reason_category=classify.OK_EMPTY,
                    endpoint=BASE, record_count=0, latency_ms=f.record.latency_ms,
                    sample=f.text[:800], requests=recs,
                    notes="200 OK but empty timeseries",
                )

            step0 = ts[0].get("data", {})
            instant = step0.get("instant", {}).get("details", {}) or {}

            # Build the field inventory from the first timestep: instant.details
            # keys, plus symbol_code + precipitation from each forecast horizon.
            fields = list(instant.keys())
            all_keys = {k.lower() for k in instant.keys()}
            symbol_codes = []
            for horizon in ("next_1_hours", "next_6_hours", "next_12_hours"):
                blk = step0.get(horizon, {}) or {}
                if not blk:
                    continue
                summ = blk.get("summary", {}) or {}
                sc = summ.get("symbol_code")
                if sc is not None:
                    fields.append(f"{horizon}.symbol_code")
                    symbol_codes.append(str(sc))
                    all_keys.add("symbol_code")
                for k in (blk.get("details", {}) or {}).keys():
                    fields.append(f"{horizon}.{k}")
                    all_keys.add(k.lower())

            # is_day is encoded by the _day/_night/_polartwilight suffix on the
            # symbol_code (MET Norway has no explicit is_day field).
            is_day_derivable = any(
                sc.endswith(("_day", "_night", "_polartwilight"))
                for sc in symbol_codes
            )

            def _has(*subs) -> bool:
                return any(any(s in k for k in all_keys) for s in subs)

            app_present_map = {
                "apparent_temperature": _has("apparent", "feels"),
                "uv_index": _has("ultraviolet", "uv_index"),
                "visibility": _has("visibility"),
                "wind_gusts": _has("gust"),
                "precipitation_probability": _has(
                    "probability_of_precip", "precipitation_probability"),
                "is_day": is_day_derivable,
            }
            present = [k for k, v in app_present_map.items() if v]
            missing = [k for k in APP_REQUIRED if not app_present_map[k]]

            units = (props.get("meta", {}) or {}).get("units", {}) or {}
            reason = classify.OK if fields else classify.OK_EMPTY
            f.record.records_parsed = len(ts)

            note = (
                f"point forecast, {len(ts)} steps; APP fields present="
                f"{present or 'none'}; missing on compact={missing}. "
                "wind_gusts/uv_index/precipitation_probability are on the "
                ".../complete endpoint; apparent_temperature & visibility are "
                "not provided by MET Norway (feels-like must be computed)."
            )
            return spec.result(
                retrievable=True, reason_category=reason, endpoint=BASE,
                fields_found=fields, record_count=len(ts), station_count=None,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes=note,
                extra={
                    "app_fields_present": present,
                    "app_fields_missing": missing,
                    "instant_details": list(instant.keys()),
                    "symbol_codes_sample": symbol_codes,
                    "is_day_via_symbol_suffix": is_day_derivable,
                    "forecast_steps": len(ts),
                    "units": units,
                    "complete_endpoint": (
                        "https://api.met.no/weatherapi/locationforecast/2.0/complete"
                    ),
                    "query": PARAMS,
                },
            )
        except Exception as exc:  # keep the run alive on any parse issue
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=BASE, latency_ms=f.record.latency_ms,
                sample=f.text[:800], requests=recs, notes="response parse failed",
            )
