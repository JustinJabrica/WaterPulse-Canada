"""
Near-real-time flood extent & marine forecasts (category="flood").

(a) SRC-NRCAN-EGS-FLOOD — NRCan Emergency Geomatics Service flood product:
    satellite-derived (RADARSAT Constellation + Sentinel-1 SAR) flood-extent
    polygons, updated near-real-time during activations. ArcGIS REST MapServer;
    we read the service descriptor (layer inventory). Event-driven — sparse
    between flood/ice-breakup activations. Licence: OGL-Canada.

(b) SRC-ECCC-MARINE — ECCC marine weather forecasts & warnings as OGC-API
    GeoJSON polygon zones (gale/squall/etc.). Flagged experimental upstream.
    Licence: OGL-Canada.
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

EGS_MAPSERVER = (
    "https://maps-cartes.services.geo.ca/egs_sgu/rest/services/"
    "Flood_Inondation/EGS_Flood_Product_Current_en/MapServer"
)
MARINE_ITEMS = "https://api.weather.gc.ca/collections/marineweather-realtime/items"


@register(
    test_id="flood-nrcan-egs-extent-ca",
    category="flood",
    source_id="SRC-NRCAN-EGS-FLOOD",
    label="NRCan EGS near-real-time SAR flood extent (ArcGIS)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
)
async def probe_egs_flood(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, EGS_MAPSERVER, source_id=spec.source_id,
            category=spec.category, params={"f": "json"}, from_metadata=True,
            notes="ArcGIS MapServer service descriptor (flood-extent layers)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=EGS_MAPSERVER, requests=recs,
            )
        try:
            data = f.json()
            layers = data.get("layers", []) if isinstance(data, dict) else []
            names = [ly.get("name") for ly in layers if isinstance(ly, dict) and ly.get("name")]
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=EGS_MAPSERVER, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(names)
        reason = classify.OK if names else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(names), reason_category=reason, endpoint=EGS_MAPSERVER,
            fields_found=names[:20], record_count=len(names),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="RCM/Sentinel-1 SAR flood-extent polygons; event-driven (sparse off-activation); "
                  "query a layer's /N/query for polygons",
        )


@register(
    test_id="flood-eccc-marine-ca",
    category="flood",
    source_id="SRC-ECCC-MARINE",
    label="ECCC marine forecasts & warnings (OGC API)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC MSC End-use Licence",
    commercial_ok="yes",
)
async def probe_marine(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, MARINE_ITEMS, source_id=spec.source_id,
            category=spec.category, params={"f": "json", "limit": 5}, from_metadata=False,
            notes="marineweather-realtime OGC items (polygon zones; experimental)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=MARINE_ITEMS, requests=recs,
            )
        try:
            data = f.json()
            feats = data.get("features", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
            number_matched = data.get("numberMatched") if isinstance(data, dict) else None
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=MARINE_ITEMS, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(feats)
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(feats), reason_category=reason, endpoint=MARINE_ITEMS,
            fields_found=fields, record_count=len(feats), station_count=number_matched,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=f"marine zones with regularForecast/warnings (numberMatched={number_matched}); "
                  "experimental schema",
            extra={"number_matched": number_matched},
        )
