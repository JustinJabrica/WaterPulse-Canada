"""
River / lake ice — ECCC scientific-knowledge datasets + CIS ice thickness.

Three sanctioned, official ECCC sources for the "ice" category, all metadata-only
(no bulk file is downloaded inline).

(a) SRC-CRID — Canadian River Ice Database. 196 National Hydrometric Program
    (NHP) sites whose observations join to WSC station numbers; period of record
    1894-2015 (freeze-up / break-up dates, ice-affected flow flags, B-dates).
(b) SRC-LAKEICE — Lake Ice Database (historical freeze-up / break-up / ice cover).
(c) SRC-CIS-ICE — Canadian Ice Service ice-thickness archive (weekly in-situ).

CRID + Lake-Ice retrieval: the `data-donnees.ec.gc.ca` directory listing now
301-redirects to a JavaScript-rendered "ECCC Data Catalogue" SPA that exposes no
static file hrefs, so scraping it yielded no evidence. Instead we query the
authoritative **open.canada.ca CKAN `package_show`** record (same technique as
`groundwater.py`), which returns the dataset's resource objects (direct download
URLs + formats) — real, machine-readable evidence of what the dataset publishes.

Licence: OGL-Canada; commercial use OK with attribution "Contains information
licensed under the Open Government Licence - Canada".
Citations: https://open.canada.ca/data/en/dataset/c5b58ccd-0011-4a80-8f24-034c86cbc14d
           https://open.canada.ca/data/en/dataset/05d08819-75b8-4f77-8688-aca5e7cce8ad
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

OPENCANADA_CKAN = "https://open.canada.ca/data/api/3/action/package_show"
CRID_ID = "c5b58ccd-0011-4a80-8f24-034c86cbc14d"
LAKEICE_ID = "05d08819-75b8-4f77-8688-aca5e7cce8ad"
CIS_THICKNESS = (
    "https://www.canada.ca/en/environment-climate-change/services/"
    "ice-forecasts-observations/latest-conditions/archive-overview/"
    "thickness-data.html"
)


async def _ckan_probe(spec, ctx: ProbeContext, dataset_id: str, note: str) -> TestResult:
    """Query open.canada.ca CKAN package_show; inventory the dataset's resources."""
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, OPENCANADA_CKAN, source_id=spec.source_id,
            category=spec.category, params={"id": dataset_id}, from_metadata=True,
            notes=f"CKAN package_show id={dataset_id}",
        )
        recs.append(f.record)
        url = f"{OPENCANADA_CKAN}?id={dataset_id}"
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
            success = bool(data.get("success")) if isinstance(data, dict) else False
            result = data.get("result", {}) if isinstance(data, dict) else {}
            if not isinstance(result, dict):
                result = {}
            resources = result.get("resources", [])
            if not isinstance(resources, list):
                resources = []
            formats = sorted({
                str(r.get("format")) for r in resources
                if isinstance(r, dict) and r.get("format")
            })
            res_names = [r.get("name") for r in resources if isinstance(r, dict)][:10]
            res_urls = [r.get("url") for r in resources
                        if isinstance(r, dict) and r.get("url")][:10]
            fields = fields_from_json(result) if result else fields_from_json(data)
            lic = result.get("license_title") or result.get("license_id")
        except Exception as exc:
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs,
            )
        if success and resources:
            reason = classify.OK
        elif success:
            reason = classify.OK_EMPTY
        else:
            reason = classify.PARSE_ERROR
        return spec.result(
            retrievable=bool(success), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(resources),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=f"{note}; {len(resources)} resources; formats={formats}; licence={lic}",
            extra={"resource_formats": formats, "resource_names": res_names,
                   "resource_urls": res_urls, "ckan_success": success},
        )


# ── (a) Canadian River Ice Database ─────────────────────────────────
@register(
    test_id="ice-crid-ca",
    category="ice",
    source_id="SRC-CRID",
    label="Canadian River Ice Database (NHP sites, freeze/break-up)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_crid(spec, ctx: ProbeContext) -> TestResult:
    res = await _ckan_probe(
        spec, ctx, CRID_ID,
        "CRID: 196 NHP sites join to WSC station numbers, 1894-2015",
    )
    # Documented dataset metadata (constant regardless of the CKAN payload).
    res.station_count = 196
    res.earliest_year = 1894
    res.latest_year = 2015
    res.span_years = 2015 - 1894 + 1
    res.extra["documented"] = {
        "nhp_sites": 196, "joins_to": "WSC station_number",
        "period_of_record": "1894-2015",
    }
    return res


# ── (b) Lake Ice Database ───────────────────────────────────────────
@register(
    test_id="ice-lakeice-ca",
    category="ice",
    source_id="SRC-LAKEICE",
    label="Lake Ice Database (freeze-up / break-up / ice cover)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_lakeice(spec, ctx: ProbeContext) -> TestResult:
    return await _ckan_probe(
        spec, ctx, LAKEICE_ID,
        "Lake Ice DB: historical lake freeze-up/break-up/ice-cover",
    )


# ── (c) CIS ice-thickness archive ───────────────────────────────────
@register(
    test_id="ice-cis-thickness-ca",
    category="ice",
    source_id="SRC-CIS-ICE",
    label="Canadian Ice Service ice-thickness archive (data page)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_cis_thickness(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, CIS_THICKNESS, source_id=spec.source_id,
            category=spec.category, from_metadata=True,
            notes="CIS ice-thickness data page (retrievability check)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=CIS_THICKNESS,
                requests=recs,
            )
        text = f.text or ""
        reason = classify.OK if text.strip() else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=CIS_THICKNESS,
            latency_ms=f.record.latency_ms, sample=text[:800], requests=recs,
            notes="CIS thickness data page reachable; in-situ ice-thickness + "
                  "on-ice snow-depth archive (metadata-only, no bulk download)",
            extra={"page_bytes": f.record.resp_bytes},
        )
