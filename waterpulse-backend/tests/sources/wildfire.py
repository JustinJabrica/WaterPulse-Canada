"""
Wildfire & smoke — CWFIS active fires + ECCC FireWork (category="wildfire").

Wildfire smoke is the dominant driver of Canadian summer AQHI, so these augment
the AQI/conditions and recreation reads directly.

(a) SRC-CWFIS-FIRE — Canadian Wildland Fire Information System (NRCan) GeoServer
    WFS. We fetch `public:hotspots_last24hrs` as GeoJSON (maxFeatures=5): point
    vectors, point-queryable. 0 rows is normal outside fire season (May–Sep).
    Licence: NRCan open data (OGL-Canada), commercial OK.
    Service: https://cwfis.cfs.nrcan.gc.ca/geoserver/public/ows
    Docs: https://cwfis.cfs.nrcan.gc.ca/downloads/docs/en/how-tos/how-to-access-cwfis-data-services.pdf

(b) SRC-ECCC-FIREWORK — ECCC FireWork (RAQDPS-FW) near-surface PM2.5 smoke
    forecast (10 km, Canada+US, hourly to 72 h). Gridded raster WMS on GeoMet;
    we confirm the RAQDPS-FW layer family via GetCapabilities (shared helper).
    Licence: ECCC End-use Licence, commercial OK.
    Docs: https://eccc-msc.github.io/open-data/msc-data/nwp_raqdps-fw/readme_raqdps-fw-geomet_en/
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.sources._geomet import probe_geomet_wms_layers
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── (a) CWFIS active-fire hotspots (WFS GeoJSON) ────────────────────
CWFIS_OWS = "https://cwfis.cfs.nrcan.gc.ca/geoserver/public/ows"


@register(
    test_id="wildfire-cwfis-hotspots-ca",
    category="wildfire",
    source_id="SRC-CWFIS-FIRE",
    label="CWFIS active-fire hotspots (last 24 h, WFS GeoJSON)",
    jurisdiction="CA",
    licence="OGL-Canada (NRCan CWFIS)",
    commercial_ok="yes",
)
async def probe_cwfis(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {
        "service": "WFS", "version": "1.0.0", "request": "GetFeature",
        "typeName": "public:hotspots_last24hrs",
        "outputFormat": "application/json", "maxFeatures": 5,
    }
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, CWFIS_OWS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="CWFIS WFS GetFeature hotspots_last24hrs (GeoJSON, maxFeatures=5)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=CWFIS_OWS, requests=recs,
            )
        try:
            data = f.json()
            feats = data.get("features", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
        except Exception as exc:  # noqa: BLE001 — parse guard (WFS may return XML)
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=CWFIS_OWS, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(feats)
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=CWFIS_OWS,
            fields_found=fields, record_count=len(feats),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="point-queryable active-fire hotspots; 0 rows normal off fire "
                  "season (May–Sep). Also: fdr_current (fire danger), "
                  "m3_polygons_current (perimeters)",
            extra={"other_layers": ["fdr_current", "hotspots_last7days",
                                    "m3_polygons_current", "activefires_current"]},
        )


# ── (b) ECCC FireWork RAQDPS-FW smoke (GeoMet WMS caps) ─────────────
@register(
    test_id="wildfire-eccc-firework-ca",
    category="wildfire",
    source_id="SRC-ECCC-FIREWORK",
    label="ECCC FireWork RAQDPS-FW near-surface PM2.5 smoke forecast",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC MSC End-use Licence",
    commercial_ok="yes",
)
async def probe_firework(spec, ctx: ProbeContext) -> TestResult:
    return await probe_geomet_wms_layers(
        spec, ctx, match_keys=("RAQDPS-FW",),
        notes="ECCC FireWork near-surface PM2.5 smoke forecast (10 km, hourly to 72 h)",
    )
