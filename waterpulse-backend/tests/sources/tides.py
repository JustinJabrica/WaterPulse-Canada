"""
Tides & coastal / tidal-river water levels — DFO/CHS IWLS API (category="tides").

The Canadian Hydrographic Service Integrated Water Level System (IWLS) is the
official REST/JSON water-level service (replacement for the retired CHS Web Data
Services). It extends WaterPulse coverage to tidal rivers and estuaries (St.
Lawrence, Fraser, Saint John, …) not served by inland hydrometric gauges, with
observed (wlo) and tidal-prediction (wlp) series. Clean per-station JSON, point-
queryable — unlike the raster GeoMet products.

SRC-CHS-IWLS — GET https://api-iwls.dfo-mpo.gc.ca/api/v1/stations
  returns a JSON array of station objects (id, code, officialName, latitude,
  longitude, type, timeSeries[…]). Time series: GET /stations/{id}/data
  ?time-series-code=wlo&from=…&to=…&resolution=FIFTEEN_MINUTES.
  Station IDs are CHS-internal (not WSC ids); vertical reference is Chart Datum.

Licence: Open Government Licence - Canada (DFO open data); commercial OK with
attribution. Docs/Swagger:
  https://api-iwls.dfo-mpo.gc.ca/swagger-ui/index.html
  https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

IWLS_STATIONS = "https://api-iwls.dfo-mpo.gc.ca/api/v1/stations"


@register(
    test_id="tides-chs-iwls-ca",
    category="tides",
    source_id="SRC-CHS-IWLS",
    label="DFO/CHS IWLS water-level stations (tides + tidal rivers/estuaries)",
    jurisdiction="CA",
    licence="OGL-Canada (DFO/CHS)",
    commercial_ok="yes",
)
async def probe_chs_iwls(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, IWLS_STATIONS, source_id=spec.source_id,
            category=spec.category, from_metadata=False,
            notes="IWLS v1 station inventory (JSON array)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=IWLS_STATIONS,
                requests=recs,
            )
        try:
            data = f.json()
            fields = fields_from_json(data)
            rc = len(data) if isinstance(data, list) else None
        except Exception as exc:  # noqa: BLE001 — parse guard
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=IWLS_STATIONS,
                sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = rc or 0
        reason = classify.OK if rc else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=IWLS_STATIONS,
            fields_found=fields, record_count=rc, station_count=rc,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="per-station JSON; wlo=observed, wlp=tidal prediction via "
                  "/stations/{id}/data; Chart Datum vertical reference",
            extra={"series_codes": ["wlo", "wlp"]},
        )
