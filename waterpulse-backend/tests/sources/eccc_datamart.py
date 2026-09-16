"""
ECCC MSC Datamart — bulk real-time hydrometric CSV (dd.weather.gc.ca).

The sanctioned, uniform, all-stations-in-one-file real-time feed for every
province/territory. One request per P/T returns every station's level/flow —
the bulk replacement for per-station scraping. Reference template for the
"current readings" category.

Licence: OGL-Canada / ECCC Data Servers End-use Licence v2.1.1 (commercial OK,
attribution "Data Source: Environment and Climate Change Canada").
Policy: contact MSC only above ~86,400 req/day (~1 req/s); no cache-bypass headers.
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, fields_from_csv, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

DATAMART = "https://dd.weather.gc.ca/today/hydrometric/csv"
PROVINCES = ["AB", "BC", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "YT", "NT", "NU"]

# Columns advertised by the Datamart hydrometric CSV readme.
EXPECTED_FIELDS = [
    "ID", "Date", "Water Level (m)", "Grade", "Symbol", "QA/QC",
    "Discharge (cms)", "Grade", "Symbol", "QA/QC",
]


async def _probe(spec, ctx: ProbeContext) -> TestResult:
    prov = spec.jurisdiction
    url = f"{DATAMART}/{prov}/hourly/{prov}_hourly_hydrometric.csv"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id, category=spec.category)
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        fields = fields_from_csv(f.text)
        lines = [ln for ln in f.text.splitlines() if ln.strip()]
        data = lines[1:] if len(lines) > 1 else []
        stations = {ln.split(",", 1)[0] for ln in data if "," in ln}
        f.record.records_parsed = len(data)
        reason = classify.OK if data else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(data), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(data), station_count=len(stations),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="hourly bulk file = last ~2 days; daily variant = last ~30 days",
            extra={"expected_fields": EXPECTED_FIELDS},
        )


for _prov in PROVINCES:
    register(
        test_id=f"current-eccc-datamart-{_prov.lower()}",
        category="current",
        source_id="SRC-ECCC-DATAMART",
        label=f"ECCC Datamart hourly bulk CSV ({_prov})",
        jurisdiction=_prov,
        licence="OGL-Canada / ECCC End-use Licence v2.1.1",
        commercial_ok="yes",
    )(_probe)
