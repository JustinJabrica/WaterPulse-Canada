"""
Water temperature — dedicated river/coastal water-temperature sources.

Two sanctioned probes for the `watertemp` category:

(a) RivTemp via DataStream (SRC-RIVTEMP)
    RivTemp (Réseau de suivi thermique des rivières) is a Canadian river
    water-temperature monitoring network whose data are published on
    DataStream. DataStream exposes an OData v4 Public API:
      Metadata endpoint: https://api.datastream.org/v1/odata/v4/Metadata
    An `x-api-key` request header is REQUIRED; unauthenticated calls return
    HTTP 401 (a *documented* outcome, not a broken URL). Rate limit ~2 req/s.
    Licence: DataStream applies a per-dataset licence chosen by each data
    provider (commonly OGL / CC-BY / custom), so reuse is *conditional* on the
    specific dataset's terms.
    Docs: https://github.com/gordonfn/datastream-api  and
          https://datastream.org/

(b) CIOOS ERDDAP (SRC-CIOOS)
    The Canadian Integrated Ocean Observing System publishes coastal/estuarine
    time series (incl. sea/water temperature) via an ERDDAP server. We probe
    the CIOOS Atlantic node's standard ERDDAP dataset-catalogue listing:
      base: https://cioosatlantic.ca/erddap/
      GET  <base>/info/index.json?itemsPerPage=10
    which returns an ERDDAP table object
    ({"table": {"columnNames":[...], "columnTypes":[...], "rows":[...]}}).
    Licence: open — CIOOS datasets are published under CC-BY / OGL / CC0
    (commercial use OK, attribution). Citation: https://cioos.ca/
    (alt ERDDAP base if the primary host moves: https://erddap.cioosatlantic.ca/erddap/)

NOTE: water temperature also appears as a FIELD embedded in other sources
covered elsewhere in the suite — the ECCC hydrometric subset, BC's real-time
feed, NL's ADRS, and NS — so `watertemp` coverage is broader than these two
dedicated networks alone.
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

# ── (a) RivTemp via DataStream OData v4 Public API ──────────────────
RIVTEMP_URL = "https://api.datastream.org/v1/odata/v4/Metadata"

# ── (b) CIOOS Atlantic ERDDAP dataset catalogue ─────────────────────
CIOOS_BASE = "https://cioosatlantic.ca/erddap/"
CIOOS_URL = CIOOS_BASE + "info/index.json"


@register(
    test_id="watertemp-rivtemp-datastream-ca",
    category="watertemp",
    source_id="SRC-RIVTEMP",
    label="RivTemp river temperature via DataStream OData v4 API",
    jurisdiction="CA",
    licence="DataStream per-dataset licence (OGL / CC-BY / custom)",
    commercial_ok="conditional",
    sanctioned=True,
)
async def probe_rivtemp(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, RIVTEMP_URL, source_id=spec.source_id,
            category=spec.category, params={"$top": 1}, from_metadata=False,
            notes="DataStream OData v4 Metadata; x-api-key header required",
        )
        recs.append(f.record)
        if not f.ok:
            # HTTP 401 with no x-api-key is the DOCUMENTED expected outcome.
            if f.record.reason_category == classify.HTTP_401:
                note = "DataStream API key required (x-api-key); 2 req/s"
            else:
                note = f"DataStream Metadata probe failed: {f.record.reason_detail}"
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=RIVTEMP_URL,
                latency_ms=f.record.latency_ms, requests=recs, notes=note,
                extra={"expected_without_key": "HTTP 401", "rate_limit": "2 req/s"},
            )
        # If a key is configured upstream and the call succeeds, inventory it.
        try:
            data = f.json()
            fields = fields_from_json(data)
            value = data.get("value") if isinstance(data, dict) else None
            rc = len(value) if isinstance(value, list) else None
        except Exception as exc:  # unparseable body
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=RIVTEMP_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes="DataStream Metadata returned unparseable body",
            )
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if fields else classify.OK_EMPTY,
            endpoint=RIVTEMP_URL, fields_found=fields, record_count=rc,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="DataStream API key present; OData v4 Metadata reachable (2 req/s)",
            extra={"rate_limit": "2 req/s"},
        )


@register(
    test_id="watertemp-cioos-erddap-multi",
    category="watertemp",
    source_id="SRC-CIOOS",
    label="CIOOS Atlantic ERDDAP dataset catalogue (coastal water temp)",
    jurisdiction="multi",
    licence="CC-BY / OGL / CC0 (per dataset)",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_cioos(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, CIOOS_URL, source_id=spec.source_id,
            category=spec.category, params={"itemsPerPage": 10}, from_metadata=False,
            notes="ERDDAP info/index.json dataset listing",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=CIOOS_URL,
                latency_ms=f.record.latency_ms, requests=recs,
                notes="CIOOS Atlantic ERDDAP info listing unreachable; "
                      f"alt base {CIOOS_BASE!r} or https://erddap.cioosatlantic.ca/erddap/",
                extra={"base": CIOOS_BASE,
                       "alt_base": "https://erddap.cioosatlantic.ca/erddap/"},
            )
        # ERDDAP returns {"table": {"columnNames":[...], "rows":[...]}}.
        try:
            data = f.json()
            table = data.get("table", {}) if isinstance(data, dict) else {}
            fields = table.get("columnNames") or fields_from_json(data)
            rows = table.get("rows")
            n_datasets = len(rows) if isinstance(rows, list) else None
        except Exception as exc:  # unparseable body
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=CIOOS_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes="CIOOS ERDDAP listing returned unparseable JSON",
            )
        f.record.records_parsed = n_datasets or 0
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if n_datasets else classify.OK_EMPTY,
            endpoint=CIOOS_URL, fields_found=fields, record_count=n_datasets,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="CIOOS Atlantic ERDDAP; itemsPerPage=10 (one catalogue page); "
                  "water temperature is a variable within many tabledap datasets",
            extra={"base": CIOOS_BASE, "datasets_on_page": n_datasets,
                   "alt_base": "https://erddap.cioosatlantic.ca/erddap/"},
        )
