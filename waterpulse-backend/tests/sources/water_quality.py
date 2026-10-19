"""
Water quality / pollution sources (category="waterquality").

Canada's water-quality data is overwhelmingly lab-analyzed grab-sample
time-series, not real-time sonde telemetry — treat it as "latest sample +
trend", architecturally separate from the real-time hydrometric probes. Neither
ECCC nor the provinces publish a national real-time in-situ WQ feed. This module
inventories the fetchable WQ networks:

(a) SRC-ECCC-WQMS  — National Long-term Water Quality Monitoring (backbone #1).
    open.canada.ca CKAN package_show metadata (OGL-Canada, commercial OK). Bulk
    CSV lives on the ECCC data mart (data-donnees.az.ec.gc.ca), keyless; we read
    catalogue metadata only here.
(b) SRC-DATASTREAM-WQ — DataStream.org OData v4 Public API (backbone #2),
    aggregating many provincial networks under one WQX-style schema. Needs an
    x-api-key header (WP_DATASTREAM_API_KEY); a 401 without a key is the
    documented outcome. Per-dataset licence (ODC-By / PDDL / OGL — all permit
    commercial use, with attribution + DOI for ODC-By / OGL).
(c) Provincial supplements, CKAN metadata-only: SRC-ON-PWQMN (OGL-Ontario),
    SRC-BC-ENMODS (OGL-BC; EMS retired 2026-03, superseded by EnMoDS),
    SRC-QC-IQBP (CC-BY 4.0), SRC-AB-RWQI (OGL-Alberta).

Recreation / swim-safety parameters to look for downstream (per dataset, not in
CKAN metadata): E. coli / fecal coliform, turbidity, and cyanobacteria /
blue-green-algae (HAB) indicators — inputs to the recreation-suitability feature.

Citation / docs:
  https://datastream.org/en-ca/documentation/api
  https://open.canada.ca/data/api/action/package_show?id=67b44816-9764-4609-ace1-68dc1764e9ea
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.sources._datastream import ODATA_BASE, datastream_headers, have_key
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── CKAN metadata probes (ECCC national + provincial) ───────────────
CKAN_ACTION = "https://open.canada.ca/data/api/action/package_show"

CKAN_SOURCES = [
    dict(
        test_id="waterquality-eccc-wqms-ca",
        source_id="SRC-ECCC-WQMS",
        label="ECCC National Long-term Water Quality Monitoring (national)",
        jurisdiction="CA",
        licence="OGL-Canada",
        commercial_ok="yes",
        ckan_id="67b44816-9764-4609-ace1-68dc1764e9ea",
        notes="backbone #1: federal freshwater quality, 2000-present; bulk CSV on "
              "the ECCC data mart (data-donnees.az.ec.gc.ca), keyless",
    ),
    dict(
        test_id="waterquality-on-pwqmn-on",
        source_id="SRC-ON-PWQMN",
        label="Ontario Provincial (Stream) Water Quality Monitoring Network",
        jurisdiction="ON",
        licence="OGL-Ontario",
        commercial_ok="yes",
        ckan_id="967a942d-9397-4e7c-8f42-77fc422c0a37",
        notes="nutrients/metals/chloride; 1964-present; CSV bulk (also on DataStream)",
    ),
    dict(
        test_id="waterquality-bc-enmods-bc",
        source_id="SRC-BC-ENMODS",
        label="BC EnMoDS water-quality results (successor to EMS)",
        jurisdiction="BC",
        licence="OGL-British Columbia",
        commercial_ok="yes",
        ckan_id="83a585fe-effb-48bd-8a03-d35db4eeb1bb",
        notes="EMS retired 2026-03-05; EnMoDS is the successor results dataset",
    ),
    dict(
        test_id="waterquality-qc-iqbp-qc",
        source_id="SRC-QC-IQBP",
        label="Quebec Reseau-rivieres physicochemical monitoring (IQBP)",
        jurisdiction="QC",
        licence="CC-BY 4.0",
        commercial_ok="yes",
        ckan_id="bf2ca474-b331-4d35-ad09-351ca8f89b27",
        notes="total P/N, chlorophyll-a, fecal coliforms, turbidity; 2000-2023; "
              "CSV / GeoJSON / ESRI REST",
    ),
    dict(
        test_id="waterquality-ab-rwqi-ab",
        source_id="SRC-AB-RWQI",
        label="Alberta River Water Quality Index / Long-Term River Network",
        jurisdiction="AB",
        licence="OGL-Alberta",
        commercial_ok="yes",
        ckan_id="50fd6eb3-e8d4-409e-8f14-313799daf2fe",
        notes="monthly at 28 LTRN sites; Alberta LTRN also on DataStream",
    ),
]
_CKAN_CONF = {c["source_id"]: c for c in CKAN_SOURCES}


async def _ckan_probe(spec, ctx: ProbeContext) -> TestResult:
    """Metadata-only retrievability check via CKAN package_show (no bulk download)."""
    conf = _CKAN_CONF[spec.source_id]
    ckan_id = conf["ckan_id"]
    endpoint = f"{CKAN_ACTION}?id={ckan_id}"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, CKAN_ACTION, source_id=spec.source_id,
            category=spec.category, params={"id": ckan_id}, from_metadata=True,
            notes=f"CKAN package_show id={ckan_id}",
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
            formats = sorted(
                {(r.get("format") or "").strip().upper()
                 for r in resources if isinstance(r, dict)} - {""}
            )
            urls = [r.get("url") for r in resources
                    if isinstance(r, dict) and r.get("url")][:5]
            title = result.get("title") or result.get("name") or ""
        except Exception as exc:  # noqa: BLE001 — parse guard, keep run alive
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
            notes=conf["notes"],
            extra={"ckan_id": ckan_id, "dataset_title": title,
                   "resource_formats": formats, "first_resource_urls": urls},
        )


for _c in CKAN_SOURCES:
    register(
        test_id=_c["test_id"], category="waterquality", source_id=_c["source_id"],
        label=_c["label"], jurisdiction=_c["jurisdiction"], licence=_c["licence"],
        commercial_ok=_c["commercial_ok"],
    )(_ckan_probe)


# ── DataStream OData v4 water-quality observations ──────────────────
DATASTREAM_WQ_URL = f"{ODATA_BASE}/Observations"


@register(
    test_id="waterquality-datastream-ca",
    category="waterquality",
    source_id="SRC-DATASTREAM-WQ",
    label="DataStream.org water-quality observations (OData v4 API)",
    jurisdiction="CA",
    licence="DataStream per-dataset (ODC-By / PDDL / OGL)",
    commercial_ok="conditional",
    sanctioned=True,
)
async def probe_datastream_wq(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"$top": 1}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, DATASTREAM_WQ_URL, source_id=spec.source_id,
            category=spec.category, params=params, headers=datastream_headers(),
            from_metadata=False,
            notes="DataStream OData v4 Observations $top=1; x-api-key header required",
        )
        recs.append(f.record)
        if not f.ok:
            if f.record.reason_category == classify.HTTP_401:
                note = ("DataStream API key required (x-api-key); set "
                        "WP_DATASTREAM_API_KEY. 401 is the documented keyless outcome")
            else:
                note = f"DataStream Observations probe failed: {f.record.reason_detail}"
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=DATASTREAM_WQ_URL,
                latency_ms=f.record.latency_ms, requests=recs, notes=note,
                extra={"expected_without_key": "HTTP 401", "rate_limit": "2 req/s",
                       "key_present": have_key()},
            )
        try:
            data = f.json()
            fields = fields_from_json(data)
            value = data.get("value") if isinstance(data, dict) else None
            rc = len(value) if isinstance(value, list) else None
        except Exception as exc:  # noqa: BLE001 — unparseable body
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=DATASTREAM_WQ_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes="DataStream Observations returned unparseable body",
            )
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if fields else classify.OK_EMPTY,
            endpoint=DATASTREAM_WQ_URL, fields_found=fields, record_count=rc,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="DataStream API key present; OData v4 Observations reachable (2 req/s). "
                  "Filter CharacteristicName for E.coli / turbidity / nutrients / metals",
            extra={"rate_limit": "2 req/s", "key_present": have_key()},
        )
