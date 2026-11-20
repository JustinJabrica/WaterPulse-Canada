"""
Road Weather Information System (RWIS) stations (category="weather").

SRC-AB-511-RWIS — 511 Alberta roadside weather stations (air/pavement temp, wind,
RH; no precip). The only 511 network found exposing queryable met-station
variables (Ontario 511 / DriveBC expose cameras + text events only). Requires a
free developer key (`?key=`) with a 10-call/60s throttle; without a key the API
returns an error — a documented outcome, like the DataStream key gate.

Set WP_511AB_API_KEY to exercise it live; otherwise this records the key gate.
Licence/commercial terms: 511 Alberta terms of use (verify before ad-supported
use → kept ad-free / status "possible" until confirmed).
Docs: https://511.alberta.ca/developers/doc
"""
from __future__ import annotations

import os

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

AB_511 = "https://511.alberta.ca/api/v2/get/weatherstations"


@register(
    test_id="weather-ab-511-rwis",
    category="weather",
    source_id="SRC-AB-511-RWIS",
    label="511 Alberta road-weather stations (key-gated)",
    jurisdiction="AB",
    licence="511 Alberta terms of use",
    commercial_ok="unknown",
    sanctioned=True,
)
async def probe_ab_511(spec, ctx: ProbeContext) -> TestResult:
    key = os.environ.get("WP_511AB_API_KEY", "").strip()
    params = {"format": "json"}
    if key:
        params["key"] = key
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, AB_511, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes="511 Alberta weatherstations; requires a free developer key (?key=)",
        )
        recs.append(f.record)
        if not f.ok:
            note = ("511 Alberta developer key required (set WP_511AB_API_KEY); "
                    "key absent is the documented outcome" if not key
                    else f"511 Alberta probe failed: {f.record.reason_detail}")
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=AB_511, requests=recs,
                notes=note, extra={"key_present": bool(key)},
            )
        try:
            data = f.json()
            rows = data if isinstance(data, list) else (data.get("Weatherstation") if isinstance(data, dict) else None) or []
            fields = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else fields_from_json(data)
        except Exception:
            # Without a key the endpoint may return HTML/error, not JSON.
            return spec.result(
                retrievable=False, reason_category=classify.HTTP_401,
                reason_detail="non-JSON body (likely key required)", endpoint=AB_511,
                sample=f.text[:800], requests=recs,
                notes="511 Alberta developer key required (set WP_511AB_API_KEY)",
                extra={"key_present": bool(key)},
            )
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=AB_511,
            fields_found=fields, record_count=len(rows), station_count=len(rows),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="air/pavement temp, wind, RH (no precip); 10 calls/60s; temps in °F",
            extra={"key_present": bool(key)},
        )
