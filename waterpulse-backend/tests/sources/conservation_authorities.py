"""
Ontario Conservation Authority real-time gauges (category="current").

Ontario's Conservation Authorities run KISTERS WISKI, exposed publicly via the
KiWIS web API — the same query grammar as the provincial Ontario Surface Water
Monitoring Centre probe (`provincial_hydro.probe_on_kiwis`). One KiWIS client
unlocks many of the 36 CAs; Grand River CA is the verified reference.

SRC-ON-GRCA — Grand River Conservation Authority KiWIS getStationList.
  https://waterdata.grandriver.ca/KiWIS/KiWIS?...&request=getStationList&format=json
  getStationList returns a JSON array whose FIRST element is the column-header
  row; remaining elements are station rows. Real-time flow/level/precip/dam-ops
  (15-min/hourly). Licence: GRCA Open Data (OGL-style); provisional until QA'd.
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_json, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

GRCA_KIWIS = "https://waterdata.grandriver.ca/KiWIS/KiWIS"
_KIWIS_PARAMS = {
    "service": "kisters", "type": "queryServices",
    "request": "getStationList", "datasource": 0, "format": "json",
}


@register(
    test_id="current-on-grca-kiwis",
    category="current",
    source_id="SRC-ON-GRCA",
    label="Grand River Conservation Authority KiWIS getStationList",
    jurisdiction="ON",
    licence="GRCA Open Data (OGL-style)",
    commercial_ok="yes",
)
async def probe_grca(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, GRCA_KIWIS, source_id=spec.source_id,
            category=spec.category, params=_KIWIS_PARAMS,
            notes="KiWIS getStationList (header row first, then stations)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=GRCA_KIWIS, requests=recs,
            )
        try:
            data = f.json()
            if isinstance(data, list) and data and isinstance(data[0], list):
                fields = [str(c) for c in data[0]]
                rows = data[1:]
            else:
                fields = fields_from_json(data)
                rows = []
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=GRCA_KIWIS, sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=GRCA_KIWIS,
            fields_found=fields, record_count=len(rows), station_count=len(rows),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="reference KiWIS client; reusable across the 36 Ontario CAs "
                  "(LSRCA/CVC/TRCA...). Values via getTimeseriesValues",
            extra={"reusable_pattern": "KiWIS getStationList/getTimeseriesValues"},
        )
