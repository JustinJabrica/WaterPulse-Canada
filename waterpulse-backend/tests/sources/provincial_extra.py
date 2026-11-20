"""
Additional provincial/territorial feeds not in the original DS-STD set
(category="current").

SRC-YT-WATER — Yukon Water Data Explorer: 15-min telemetry (level, flow, air
temp, wind) + lab water quality + snow survey, catalogued on the Yukon open-data
CKAN portal. Metadata-only retrievability check via CKAN package_show (the live
telemetry sits behind a Shiny app / downloadable resources). Licence: Yukon open
data (confirm commercial terms before ad-supported use).

(NS automated surface-water quality, PE near-real-time groundwater, and NB River
Watch / GeoNB flood are catalogued as "possible" in the frontend source registry;
their machine endpoints need resolution before probing and are intentionally left
at that status until verified.)
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

YT_CKAN = "https://open.yukon.ca/api/3/action/package_show"
YT_ID = "water-data-explorer"


@register(
    test_id="current-yt-water-explorer",
    category="current",
    source_id="SRC-YT-WATER",
    label="Yukon Water Data Explorer (CKAN metadata)",
    jurisdiction="YT",
    licence="Yukon open data (confirm)",
    commercial_ok="unknown",
)
async def probe_yukon(spec, ctx: ProbeContext) -> TestResult:
    endpoint = f"{YT_CKAN}?id={YT_ID}"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, YT_CKAN, source_id=spec.source_id,
            category=spec.category, params={"id": YT_ID}, from_metadata=True,
            notes=f"CKAN package_show id={YT_ID}",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=endpoint, requests=recs,
            )
        try:
            data = f.json()
            if not isinstance(data, dict) or not data.get("success", False):
                return spec.result(
                    retrievable=False, reason_category=classify.PARSE_ERROR,
                    reason_detail="CKAN success=false or non-object", endpoint=endpoint,
                    sample=f.text[:800], requests=recs,
                )
            result = data.get("result", {}) or {}
            resources = result.get("resources", []) or []
            formats = sorted({(r.get("format") or "").strip().upper()
                              for r in resources if isinstance(r, dict)} - {""})
            title = result.get("title") or result.get("name") or ""
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=endpoint, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(resources)
        reason = classify.OK if resources else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(resources), reason_category=reason, endpoint=endpoint,
            fields_found=formats, record_count=len(resources),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="15-min level/flow/met + WQ + snow survey; live data via Shiny/resource files "
                  "(no clean REST API yet)",
            extra={"ckan_id": YT_ID, "dataset_title": title},
        )
