"""
Flood forecast / advisory sources (category="flood").

Canada has no single national flood-status API; the operational picture is
stitched from a federal prediction backbone plus per-jurisdiction warning
feeds of very uneven machine-readability. This module inventories the ones
that matter:

(a) SRC-ECCC-WATERPRED — ECCC GeoMet OGC API "collections" catalogue
    (api.weather.gc.ca). We list every collection whose id looks like a
    water-prediction product (WCPS deterministic/probabilistic water cycle
    prediction, OHPS operational hydrologic prediction, storm-surge, etc.).
    Endpoint: https://api.weather.gc.ca/collections?f=json
    Licence: OGL-Canada / ECCC End-use Licence (commercial OK, attribution).

(b) SRC-NRCAN-FLOOD — NRCan Flood Hazard Identification and Mapping Program
    (FHIMP) landing / flood-mapping hub on geo.ca. HTML retrievability check
    (federal open data, OGL-Canada). https://geo.ca/flood-mapping/

(c) SRC-BC-RFC — BC River Forecast Centre "Flood Warning and Advisory
    Notifications". Published as an ArcGIS Online hosted FeatureServer
    (Public View). We query 5 records. Licence: OGL-BC (commercial OK).
    Service: services6.arcgis.com/ubm4tcTYICKBpist/.../
             BC_Flood_Advisory_and_Warning_Notifications_(Public_View)/FeatureServer/0
    Fallback: RFC warnings page https://bcrfc.env.gov.bc.ca/warnings/index.htm

(d) SRC-QC-VIGILANCE — Québec "Vigilance — Surveillance de la crue des eaux"
    WFS (geoegl.msp.gouv.qc.ca). The public hydrometric-station WFS also
    carries flood-status attributes. Light GetFeature (maxFeatures=1,
    outputFormat=geojson). Licence: CC-BY 4.0 (Québec).
    Service: https://geoegl.msp.gouv.qc.ca/apis/mapserver-vigilance/ws/vigilance.fcgi

(e) SRC-ON-CO — Conservation Ontario flood forecasting & warning hub, and
    SRC-MB-HFC — Manitoba Hydrologic Forecast Centre. Both are HTML/PDF only
    (no machine API); we do a page-retrievability check and flag the gap.

Citation / references:
  https://eccc-msc.github.io/open-data/msc-geomet/readme_en/
  https://geo.ca/flood-mapping/
  https://bcrfc.env.gov.bc.ca/warnings/index.htm
  https://geoegl.msp.gouv.qc.ca/adnv2/carte.php
"""
from __future__ import annotations

import re

from tests.sources._base import (
    ProbeContext,
    fields_from_json,
    http_probe,
    register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── (a) ECCC GeoMet water-prediction WMS layers ─────────────────────
# WCPS/OHPS/RIOPS/CIOPS/storm-surge are gridded WMS/coverage products, NOT
# OGC-API-Features collections (the api.weather.gc.ca/collections catalogue
# contains no such id — confirmed), so we enumerate them from the GeoMet WMS
# GetCapabilities layer inventory (the same GetCapabilities technique the working
# GIN groundwater probe uses). The caps document is large; timeout is raised.
GEOMET_WMS = "https://geo.weather.gc.ca/geomet"
_WATER_PRED_KEYS = ("WCPS", "OHPS", "DHPS", "RDWPS", "GDWPS", "RIOPS", "CIOPS", "SURGE")


async def _probe_eccc_waterpred(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetCapabilities", "lang": "en"}
    async with build_client(timeout=max(120.0, ctx.request_timeout)) as client:
        f = await http_probe(
            ctx, client, GEOMET_WMS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="GeoMet WMS 1.3.0 GetCapabilities (water-prediction layers)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=GEOMET_WMS, requests=recs,
            )
        text = f.text or ""
        names = re.findall(r"<Name>([^<]+)</Name>", text)
        matched = sorted({n for n in names if any(k in n.upper() for k in _WATER_PRED_KEYS)})
        is_caps = ("WMS_Capabilities" in text or "WMT_MS_Capabilities" in text
                   or "<Layer" in text)
        if not is_caps:
            reason = classify.PARSE_ERROR
        elif matched:
            reason = classify.OK
        else:
            reason = classify.OK_EMPTY
        f.record.records_parsed = len(matched)
        return spec.result(
            retrievable=bool(matched), reason_category=reason, endpoint=GEOMET_WMS,
            fields_found=matched[:40], record_count=len(matched),
            latency_ms=f.record.latency_ms, sample="; ".join(matched[:20])[:800],
            requests=recs,
            notes=f"{len(matched)} water-prediction WMS layers "
                  f"(WCPS/OHPS/DHPS/RIOPS/CIOPS/surge) of {len(names)} total <Name> in caps",
            extra={"match_keys": list(_WATER_PRED_KEYS), "total_layer_names": len(names)},
        )


# ── (c) BC River Forecast Centre flood notifications (ArcGIS) ────────
BC_RFC_FS = (
    "https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/"
    "BC_Flood_Advisory_and_Warning_Notifications_(Public_View)/FeatureServer/0/query"
)


async def _probe_bc_rfc(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"where": "1=1", "outFields": "*", "f": "json", "resultRecordCount": 5}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, BC_RFC_FS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="ArcGIS FeatureServer query (5 records)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=BC_RFC_FS,
                requests=recs,
            )
        try:
            data = f.json()
            features = data.get("features", []) if isinstance(data, dict) else []
            fields = []
            if features and isinstance(features[0], dict):
                first = features[0]
                attrs = first.get("attributes") or first.get("properties") or {}
                fields = list(attrs.keys())
                if "geometry" in first:
                    fields.append("geometry")
            if not fields:
                # ArcGIS also advertises the schema even when 0 rows match
                fld_defs = data.get("fields", []) if isinstance(data, dict) else []
                fields = [d.get("name") for d in fld_defs if isinstance(d, dict) and d.get("name")]
        except Exception as exc:  # pragma: no cover - defensive parse guard
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=BC_RFC_FS,
                sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(features)
        reason = classify.OK if features else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=BC_RFC_FS,
            fields_found=fields, record_count=len(features),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="0 rows is normal when no active flood warnings/advisories",
            extra={},
        )


# ── (d) Québec Vigilance flood-surveillance WFS ─────────────────────
QC_VIGILANCE_WFS = "https://geoegl.msp.gouv.qc.ca/apis/mapserver-vigilance/ws/vigilance.fcgi"
QC_VIGILANCE_TYPENAME = "stations_igo2_public"


async def _probe_qc_vigilance(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {
        "service": "WFS", "version": "1.1.0", "request": "GetFeature",
        "typename": QC_VIGILANCE_TYPENAME, "maxfeatures": 1,
        "outputformat": "geojson",
    }
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, QC_VIGILANCE_WFS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="WFS GetFeature maxfeatures=1 (geojson)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=QC_VIGILANCE_WFS,
                requests=recs,
            )
        fields: list[str] = []
        rc: int | None = None
        try:
            data = f.json()
            fields = fields_from_json(data)
            if isinstance(data, dict) and isinstance(data.get("features"), list):
                rc = len(data["features"])
        except Exception:
            # WFS may return GML/XML rather than GeoJSON — still a valid payload.
            data = None
        blob = f.text.lower()
        got_data = bool(fields) or any(
            tok in blob for tok in ("featurecollection", "gml", "<wfs", "\"features\"")
        )
        reason = classify.OK if got_data else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=QC_VIGILANCE_WFS,
            fields_found=fields, record_count=rc,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="Vigilance station WFS also carries flood-status attributes; "
                  "GeoJSON if outputformat honoured, otherwise GML/XML",
            extra={"typename": QC_VIGILANCE_TYPENAME},
        )


# ── (b)+(e) HTML-only retrievability checks (no machine API) ─────────
async def _probe_html(spec, ctx: ProbeContext, url: str, note: str) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, url, source_id=spec.source_id, category=spec.category,
            from_metadata=True, notes=note,
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                notes=note,
            )
        has_body = bool(f.text.strip())
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if has_body else classify.OK_EMPTY,
            endpoint=url, fields_found=[], record_count=None,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=note,
            extra={"content_type": (f.response.headers.get("Content-Type", "")
                                    if f.response is not None else "")},
        )


# (b) NRCan FHIMP flood-mapping hub
NRCAN_FHIMP = "https://geo.ca/flood-mapping/"


async def _probe_nrcan_fhimp(spec, ctx: ProbeContext) -> TestResult:
    return await _probe_html(
        spec, ctx, NRCAN_FHIMP,
        "FHIMP flood-mapping hub (HTML landing); bulk layers via geo.ca catalogue",
    )


# (e) Conservation Ontario flood forecasting & warning
ON_CO_URL = ("https://conservationontario.ca/conservation-authorities/"
             "flood-erosion-management/flood-messages")


async def _probe_on_co(spec, ctx: ProbeContext) -> TestResult:
    return await _probe_html(
        spec, ctx, ON_CO_URL,
        "HTML/PDF only, no API; 36 conservation authorities issue local flood messages",
    )


# (e) Manitoba Hydrologic Forecast Centre
MB_HFC_URL = "https://www.gov.mb.ca/mit/floodinfo/forecast_centre/index.html"


async def _probe_mb_hfc(spec, ctx: ProbeContext) -> TestResult:
    return await _probe_html(
        spec, ctx, MB_HFC_URL,
        "HTML/PDF only, no API; MB Transportation & Infrastructure flood bulletins",
    )


# ── Registration ────────────────────────────────────────────────────
register(
    test_id="flood-eccc-waterpred-ca",
    category="flood",
    source_id="SRC-ECCC-WATERPRED",
    label="ECCC GeoMet water-prediction collections (WCPS/OHPS/surge)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC End-use Licence",
    commercial_ok="yes",
)(_probe_eccc_waterpred)

register(
    test_id="flood-nrcan-fhimp-ca",
    category="flood",
    source_id="SRC-NRCAN-FLOOD",
    label="NRCan FHIMP flood-mapping hub (geo.ca)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
)(_probe_nrcan_fhimp)

register(
    test_id="flood-bc-rfc-notifications",
    category="flood",
    source_id="SRC-BC-RFC",
    label="BC River Forecast Centre flood warning/advisory notifications (ArcGIS)",
    jurisdiction="BC",
    licence="OGL-BC",
    commercial_ok="yes",
)(_probe_bc_rfc)

register(
    test_id="flood-qc-vigilance",
    category="flood",
    source_id="SRC-QC-VIGILANCE",
    label="Québec Vigilance flood-surveillance WFS",
    jurisdiction="QC",
    licence="CC-BY 4.0 (Québec)",
    commercial_ok="yes",
)(_probe_qc_vigilance)

register(
    test_id="flood-on-conservation-ontario",
    category="flood",
    source_id="SRC-ON-CO",
    label="Conservation Ontario flood forecasting & warning (HTML/PDF)",
    jurisdiction="ON",
    licence="Conservation Ontario terms (unspecified)",
    commercial_ok="unknown",
    sanctioned=True,
)(_probe_on_co)

register(
    test_id="flood-mb-hfc",
    category="flood",
    source_id="SRC-MB-HFC",
    label="Manitoba Hydrologic Forecast Centre (HTML/PDF)",
    jurisdiction="MB",
    licence="Manitoba open terms (unspecified)",
    commercial_ok="unknown",
    sanctioned=True,
)(_probe_mb_hfc)
