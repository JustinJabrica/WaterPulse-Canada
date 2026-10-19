"""
Shared GeoMet WMS GetCapabilities helper.

ECCC's GeoMet WMS (https://geo.weather.gc.ca/geomet) publishes hundreds of
raster map layers — radar, precip analysis/forecast, lightning, wildfire smoke,
and the water-prediction model families. Several probes need the identical
move: fetch the WMS 1.3.0 GetCapabilities document and confirm a family of
layers (matched by `<Name>` substring) is advertised. This factors that out of
`flood.py` so the radar / lightning / HRDPA / FireWork probes — and the original
water-prediction probe — all reuse one implementation.

The GetCapabilities document is large; the timeout is raised to >=120 s (same as
the original flood water-prediction probe). This is a metadata-only, read-only
retrievability check: one request, no coverage grid is ever fetched.

Licence for every GeoMet layer: ECCC MSC Data Servers End-use Licence
(commercial OK, attribution "Data Source: Environment and Climate Change Canada").
"""
from __future__ import annotations

import re

from tests.sources._base import ProbeContext, http_probe
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

GEOMET_WMS = "https://geo.weather.gc.ca/geomet"


async def probe_geomet_wms_layers(
    spec,
    ctx: ProbeContext,
    *,
    match_keys: tuple[str, ...],
    notes: str,
    endpoint: str = GEOMET_WMS,
    lang: str = "en",
) -> TestResult:
    """Fetch GeoMet WMS 1.3.0 GetCapabilities and report every layer whose
    `<Name>` contains any of `match_keys` (case-insensitive substring).

    `retrievable` is True when at least one matching layer is advertised. A
    reachable caps document with no matching layer is OK_EMPTY (the family may
    have been renamed/retired upstream — a data gap, not our bug), and a body
    that is not a caps document at all is PARSE_ERROR.
    """
    recs = []
    params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetCapabilities", "lang": lang}
    async with build_client(timeout=max(120.0, ctx.request_timeout)) as client:
        f = await http_probe(
            ctx, client, endpoint, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="GeoMet WMS 1.3.0 GetCapabilities",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=endpoint, requests=recs,
            )
        text = f.text or ""
        names = re.findall(r"<Name>([^<]+)</Name>", text)
        keys_up = tuple(k.upper() for k in match_keys)
        matched = sorted({n for n in names if any(k in n.upper() for k in keys_up)})
        is_caps = (
            "WMS_Capabilities" in text or "WMT_MS_Capabilities" in text or "<Layer" in text
        )
        if not is_caps:
            reason = classify.PARSE_ERROR
        elif matched:
            reason = classify.OK
        else:
            reason = classify.OK_EMPTY
        f.record.records_parsed = len(matched)
        return spec.result(
            retrievable=bool(matched), reason_category=reason, endpoint=endpoint,
            fields_found=matched[:40], record_count=len(matched),
            latency_ms=f.record.latency_ms, sample="; ".join(matched[:20])[:800],
            requests=recs,
            notes=f"{notes}; matched {len(matched)} of {len(names)} total <Name> layers",
            extra={"match_keys": list(match_keys), "total_layer_names": len(names)},
        )
