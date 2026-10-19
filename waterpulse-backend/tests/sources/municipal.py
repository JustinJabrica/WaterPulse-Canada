"""
Municipal open-data water sources (category="municipal").

Cities publish creek/river gauges, combined-sewer-overflow (CSO), and beach
water-quality data through open-data portals — Socrata (data.<city>.ca) and CKAN
(open.toronto.ca, donnees.montreal.ca). These fill the sub-watershed / urban gap
that federal + provincial gauges miss. Many "water level" datasets re-serve WSC
gauges, so dedupe by station id against HYDAT before treating as net-new.

Socrata (live data sample): GET https://data.<city>.ca/resource/<id>.json?$limit=5
CKAN (metadata): GET <portal>/api/3/action/package_show?id=<slug>

Licences: each city's Open Government Licence (commercial OK) except Montréal
RSMA which is CC-BY 4.0 (commercial OK).
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext, fields_from_json, freshness_from, http_probe, register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── Socrata city feeds (live rows) ──────────────────────────────────
SOCRATA = [
    dict(test_id="municipal-calgary-rivers", source_id="SRC-CITY-CALGARY",
         label="City of Calgary river levels & flows (Socrata, 5-min)",
         jurisdiction="AB", url="https://data.calgary.ca/resource/5fdg-ifgr.json",
         order="timestamp DESC",
         notes="Bow/Elbow level+flow ~5-min; some sites overlap WSC — dedupe by station id"),
    dict(test_id="municipal-edmonton-rivers", source_id="SRC-CITY-EDMONTON",
         label="City of Edmonton water levels & flows (Socrata)",
         jurisdiction="AB", url="https://data.edmonton.ca/resource/cnsu-iagr.json",
         order=None, notes="N. Saskatchewan + Sturgeon stations"),
    dict(test_id="municipal-winnipeg-rivers", source_id="SRC-CITY-WINNIPEG",
         label="City of Winnipeg river levels (Socrata; CSO dataset 9pyh-i7a4)",
         jurisdiction="MB", url="https://data.winnipeg.ca/resource/tgrf-v2zc.json",
         order=None, notes="Red + Assiniboine city sites; CSO-discharge feed also available"),
]


async def _socrata_probe(spec, ctx: ProbeContext) -> TestResult:
    conf = next(c for c in SOCRATA if c["source_id"] == spec.source_id)
    params = {"$limit": 5}
    if conf["order"]:
        params["$order"] = conf["order"]
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, conf["url"], source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="Socrata SODA JSON sample",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=conf["url"], requests=recs,
            )
        try:
            data = f.json()
            rows = data if isinstance(data, list) else []
            fields = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
            # gather candidate timestamps from all string cells
            strings = [v for r in rows if isinstance(r, dict) for v in r.values() if isinstance(v, str)]
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=conf["url"], sample=f.text[:800], requests=recs,
            )
        latest_obs, age_min = freshness_from(strings)
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=conf["url"],
            fields_found=fields, record_count=len(rows),
            latency_ms=f.record.latency_ms, latest_obs_utc=latest_obs, data_age_minutes=age_min,
            sample=f.text[:800], requests=recs, notes=conf["notes"],
        )


for _c in SOCRATA:
    register(test_id=_c["test_id"], category="municipal", source_id=_c["source_id"],
             label=_c["label"], jurisdiction=_c["jurisdiction"],
             licence="Open Government Licence – City", commercial_ok="yes")(_socrata_probe)


# ── CKAN city feeds (beach water quality — metadata) ────────────────
CKAN = [
    dict(test_id="municipal-toronto-beaches", source_id="SRC-CITY-TORONTO-BEACH",
         label="City of Toronto beach water quality (E. coli)", jurisdiction="ON",
         action="https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show",
         ckan_id="toronto-beaches-water-quality", licence="OGL-Toronto",
         notes="daily E. coli, Jun–Sep; lab-confirmed (~1 day lag)"),
    dict(test_id="municipal-montreal-rsma", source_id="SRC-CITY-MONTREAL-RSMA",
         label="Montréal RSMA riverbank/beach water quality (QUALO)", jurisdiction="QC",
         action="https://donnees.montreal.ca/api/3/action/package_show",
         ckan_id="rsma-qualite-de-l-eau-en-rive-qualo", licence="CC-BY 4.0",
         notes="~500 stations, weekly May–Nov; fecal coliforms, temp, conductivity, pH"),
]


async def _ckan_probe(spec, ctx: ProbeContext) -> TestResult:
    conf = next(c for c in CKAN if c["source_id"] == spec.source_id)
    endpoint = f"{conf['action']}?id={conf['ckan_id']}"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, conf["action"], source_id=spec.source_id,
            category=spec.category, params={"id": conf["ckan_id"]}, from_metadata=True,
            notes=f"CKAN package_show id={conf['ckan_id']}",
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
            notes=conf["notes"], extra={"ckan_id": conf["ckan_id"], "dataset_title": title},
        )


for _c in CKAN:
    register(test_id=_c["test_id"], category="municipal", source_id=_c["source_id"],
             label=_c["label"], jurisdiction=_c["jurisdiction"],
             licence=_c["licence"], commercial_ok="yes")(_ckan_probe)
