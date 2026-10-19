"""
Groundwater levels — federal + provincial monitoring networks.

Category: groundwater. Four sanctioned, low-load, read-only sources:

(a) SRC-STA-GW — Geological Survey of Canada federal OGC SensorThings API (STA)
    Base: https://mon.geosciences.ca/sta/
    Probe the OData `Things` collection (`Things?$top=5`) for a small national
    sample, then per-province samples via `$filter=properties/prov eq <code>`
    (ON=2, QC=7; other provinces exist but are not looped, to stay light). The
    provinces actually present are recorded from each Thing's `properties`.
    Licence: OGL-Canada (commercial OK, attribution to NRCan/GSC).

(b) SRC-GIN — Groundwater Information Network (GIN) OGC WMS mediator.
    GetCapabilities:
      https://gin.geosciences.ca/service/gin/wms/mediator/gin_en
      ?request=GetCapabilities&service=WMS&version=1.3.0
    Metadata-only retrievability check; the WMS layer inventory is the
    "field" signal (count of `<Layer` elements in the capabilities XML).
    Licence: OGL-Canada.

(c) SRC-ON-PGMN — Ontario Provincial Groundwater Monitoring Network (PGMN).
    CKAN package_show:
      https://data.ontario.ca/api/3/action/package_show
      ?id=provincial-groundwater-monitoring-network
    Licence: Open Government Licence – Ontario (commercial OK, attribution).

(d) SRC-QC-RSESQ — Quebec Reseau de suivi des eaux souterraines du Quebec.
    CKAN package_show (Donnees Quebec):
      https://www.donneesquebec.ca/recherche/api/3/action/package_show?id=rsesq
    Licence: CC-BY 4.0 (commercial OK, attribution).

Citation URLs:
  https://gin.geosciences.ca/  (GIN / NGWDS)
  https://data.ontario.ca/dataset/provincial-groundwater-monitoring-network
  https://www.donneesquebec.ca/recherche/dataset/rsesq
"""
from __future__ import annotations

from urllib.parse import quote

from tests.sources._base import (
    ProbeContext,
    fields_from_csv,
    fields_from_json,
    http_probe,
    register,
    year_span,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── (a) Federal GSC SensorThings API ────────────────────────────────
STA_BASE = "https://mon.geosciences.ca/sta/"
# properties/prov codes advertised by GIN/STA; loop only ON & QC to stay light.
STA_PROV = {"ON": 2, "QC": 7}

# ── (b) GIN WMS mediator ────────────────────────────────────────────
GIN_WMS_CAPS = (
    "https://gin.geosciences.ca/service/gin/wms/mediator/gin_en"
    "?request=GetCapabilities&service=WMS&version=1.3.0"
)

# ── (c)/(d) CKAN package_show endpoints ─────────────────────────────
CKAN = {
    "SRC-ON-PGMN": {
        "base": "https://data.ontario.ca",
        "id": "provincial-groundwater-monitoring-network",
    },
    "SRC-QC-RSESQ": {
        "base": "https://www.donneesquebec.ca/recherche",
        "id": "rsesq",
    },
}


# ── (a) SensorThings: national sample ───────────────────────────────
async def _sta_national(spec, ctx: ProbeContext) -> TestResult:
    url = f"{STA_BASE}Things?$top=5"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, notes="OData Things $top=5")
        recs.append(f.record)
        if not f.ok:
            return spec.result(retrievable=False, reason_category=f.record.reason_category,
                               reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
        try:
            data = f.json()
            value = data.get("value", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
            iot_count = data.get("@iot.count") if isinstance(data, dict) else None
            provinces = sorted({
                str(v["properties"]["prov"])
                for v in value
                if isinstance(v, dict) and isinstance(v.get("properties"), dict)
                and v["properties"].get("prov") is not None
            })
        except Exception as exc:  # unparseable body
            _, detail = classify.classify_exception(exc)
            return spec.result(retrievable=False, reason_category=classify.PARSE_ERROR,
                               reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs)
        reason = classify.OK if value else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(value), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(value),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="GSC federal SensorThings groundwater; Things $top=5 national sample",
            extra={"iot_count": iot_count, "provinces_seen": provinces,
                   "prov_codes_available": STA_PROV},
        )


# ── (a) SensorThings: per-province sample ───────────────────────────
async def _sta_province(spec, ctx: ProbeContext) -> TestResult:
    code = STA_PROV[spec.jurisdiction]
    filt = quote(f"properties/prov eq {code}", safe="/")
    url = f"{STA_BASE}Things?$filter={filt}&$top=5"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, notes=f"OData filter prov eq {code}")
        recs.append(f.record)
        if not f.ok:
            return spec.result(retrievable=False, reason_category=f.record.reason_category,
                               reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
        try:
            data = f.json()
            value = data.get("value", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
            iot_count = data.get("@iot.count") if isinstance(data, dict) else None
        except Exception as exc:
            _, detail = classify.classify_exception(exc)
            return spec.result(retrievable=False, reason_category=classify.PARSE_ERROR,
                               reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs)
        reason = classify.OK if value else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(value), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(value),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=f"{spec.jurisdiction} groundwater Things (properties/prov eq {code})",
            extra={"prov_code": code, "iot_count": iot_count},
        )


# ── (b) GIN WMS GetCapabilities ─────────────────────────────────────
async def _gin_wms(spec, ctx: ProbeContext) -> TestResult:
    url = GIN_WMS_CAPS
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, from_metadata=True,
                             notes="WMS 1.3.0 GetCapabilities")
        recs.append(f.record)
        if not f.ok:
            return spec.result(retrievable=False, reason_category=f.record.reason_category,
                               reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
        text = f.text or ""
        n_layers = text.count("<Layer")
        is_caps = ("WMS_Capabilities" in text or "WMT_MS_Capabilities" in text
                   or n_layers > 0)
        if not is_caps:
            reason = classify.PARSE_ERROR
        elif n_layers:
            reason = classify.OK
        else:
            reason = classify.OK_EMPTY
        return spec.result(
            retrievable=bool(is_caps), reason_category=reason, endpoint=url,
            fields_found=[f"layers:{n_layers}"] if n_layers else [],
            record_count=n_layers if n_layers else None,
            latency_ms=f.record.latency_ms, sample=text[:800], requests=recs,
            notes=f"GIN WMS GetCapabilities; {n_layers} <Layer> elements",
            extra={"layer_count": n_layers},
        )


# ── (c)/(d) CKAN package_show ───────────────────────────────────────
async def _ckan_probe(spec, ctx: ProbeContext) -> TestResult:
    cfg = CKAN[spec.source_id]
    base = f"{cfg['base']}/api/3/action/package_show"
    url = f"{base}?id={cfg['id']}"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, base, source_id=spec.source_id,
                             category=spec.category, params={"id": cfg["id"]},
                             from_metadata=True, notes=f"CKAN package_show id={cfg['id']}")
        recs.append(f.record)
        if not f.ok:
            return spec.result(retrievable=False, reason_category=f.record.reason_category,
                               reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
        try:
            data = f.json()
            success = bool(data.get("success")) if isinstance(data, dict) else False
            result = data.get("result", {}) if isinstance(data, dict) else {}
            if not isinstance(result, dict):
                result = {}
            resources = result.get("resources", [])
            if not isinstance(resources, list):
                resources = []
            fields = fields_from_json(result) if result else fields_from_json(data)
            formats = sorted({
                str(r.get("format")) for r in resources
                if isinstance(r, dict) and r.get("format")
            })
            res_names = [r.get("name") for r in resources if isinstance(r, dict)][:10]
            lic = result.get("license_title") or result.get("license_id")
        except Exception as exc:
            _, detail = classify.classify_exception(exc)
            return spec.result(retrievable=False, reason_category=classify.PARSE_ERROR,
                               reason_detail=detail, endpoint=url, sample=f.text[:800], requests=recs)
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
            notes=f"CKAN package '{cfg['id']}'; {len(resources)} resources; licence={lic}",
            extra={"resource_formats": formats, "resource_names": res_names,
                   "ckan_license": lic, "ckan_success": success},
        )


# ── Registration ────────────────────────────────────────────────────
# (a) Federal SensorThings — national sample
register(
    test_id="groundwater-sta-gw-ca",
    category="groundwater",
    source_id="SRC-STA-GW",
    label="GSC SensorThings groundwater (national Things $top=5)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
)(_sta_national)

# (a) Federal SensorThings — per-province (ON, QC only; others exist)
for _juris in ("ON", "QC"):
    register(
        test_id=f"groundwater-sta-gw-{_juris.lower()}",
        category="groundwater",
        source_id="SRC-STA-GW",
        label=f"GSC SensorThings groundwater ({_juris}, prov eq {STA_PROV[_juris]})",
        jurisdiction=_juris,
        licence="OGL-Canada",
        commercial_ok="yes",
    )(_sta_province)

# (b) GIN WMS GetCapabilities
register(
    test_id="groundwater-gin-wms-ca",
    category="groundwater",
    source_id="SRC-GIN",
    label="GIN WMS GetCapabilities (national groundwater layers)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
)(_gin_wms)

# (c) Ontario PGMN (CKAN)
register(
    test_id="groundwater-on-pgmn",
    category="groundwater",
    source_id="SRC-ON-PGMN",
    label="Ontario PGMN (data.ontario.ca CKAN package_show)",
    jurisdiction="ON",
    licence="OGL-Ontario",
    commercial_ok="yes",
)(_ckan_probe)

# (d) Quebec RSESQ (CKAN)
register(
    test_id="groundwater-qc-rsesq",
    category="groundwater",
    source_id="SRC-QC-RSESQ",
    label="Quebec RSESQ (Donnees Quebec CKAN package_show)",
    jurisdiction="QC",
    licence="CC-BY 4.0",
    commercial_ok="yes",
)(_ckan_probe)
