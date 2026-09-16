"""
Provincial PRIMARY river feeds (water level / flow) — the province-run
real-time hydrometric sources that sit alongside (and sometimes ahead of) the
federal ECCC/WSC network. Each province publishes its "current readings"
differently, so this module carries one probe per jurisdiction with mixed
sanction flags: the documented, machine-readable feeds are sanctioned; the
scrape-only / undocumented / connection-refusing ones are marked
``sanctioned=False`` so ``probe_sources`` skips them (they run only in the
user-launched residual harness).

Probes / endpoints / licences (citation URLs):
  (a) SRC-MB-FLOODINFO — Manitoba Flood Information / Forecast Centre AGOL feed.
      CSV: https://www.manitoba.ca/floodinfo/floodoutlook/forecast_centre/agol/agoldataV2.csv
      Fields include measuredFlow / measuredLevel / forecastedFlow / floodStage /
      alert (units: feet + cfs). Licence: OpenMB (Manitoba Open Government
      Licence). Portal: https://www.manitoba.ca/flooding/
  (b) SRC-ON-KIWIS — Ontario MNRF Surface Water Monitoring Centre KiWIS.
      getStationList JSON (first array element is the column header row):
      https://www.swmc.mnr.gov.on.ca/KiWIS/KiWIS?service=kisters&type=queryServices
        &request=getStationList&datasource=0&format=json
      Licence: Open Government Licence – Ontario. Portal:
      https://www.ontario.ca/page/surface-water-monitoring
  (c) SRC-QC-VIGILANCE — Québec MELCCFP / Vigilance (hydrometric stations).
      WFS GeoJSON: https://geoegl.msp.gouv.qc.ca/apis/mapserver-vigilance/ws/vigilance.fcgi
      typename stations_igo2_public; props include dern_valeur_niv / dern_valeur_deb.
      Licence: CC-BY 4.0 (Québec). Portal: https://vigilance.gouv.qc.ca/
  (d) SRC-NL-ADRS — Newfoundland & Labrador Water Resources Management Div. ADRS.
      Per-station CSV: https://www.mae.gov.nl.ca/wrmd/adrs/v6/Data/02YL008_Line.csv
      Header STAT_NUM,WSC_NUM,NST_DATI,WATER_TEMP,STAGE,FLOW,BATT_VOLTAGE (note the
      WATER_TEMP column). Licence: Open Government Licence – Newfoundland and
      Labrador. Portal: https://www.gov.nl.ca/ecc/waterres/realtime/
  (e) SRC-AB-RIVERS — Alberta Environment & Parks "Alberta River Basins".
      Discovery: https://rivers.alberta.ca/DataService/ListStationsAndAlerts
      (per-station static JSON + porExtracts CSV downstream). Licence: Government
      of Alberta copyright — NON-COMMERCIAL. The host aggressively refuses
      connections to non-browser clients, so a ``connect_refused`` result is the
      expected/valid evidence. sanctioned=False.
  (f) SRC-BC-AQUARIUS — BC ENV AQUARIUS WebPortal (undocumented export/JSON).
      Best-effort: https://bcmoe-prod.aquaticinformatics.net/Data/Data_List
      Licence: Open Government Licence – British Columbia. sanctioned=False.
  (g) SRC-SK-WSA — Saskatchewan Water Security Agency hydrographs.
      Scrape-only (embedded dygraphs htmlwidget; values not in a data endpoint):
      https://www.wsask.ca/hydrographs/05MB006-hrly.html
      Licence: SK Crown copyright (no written permission = no commercial use).
      sanctioned=False.
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext,
    fields_from_csv,
    fields_from_json,
    http_probe,
    register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult


# ── (a) Manitoba FloodInfo / Forecast Centre AGOL CSV ───────────────────
MB_URL = (
    "https://www.manitoba.ca/floodinfo/floodoutlook/forecast_centre/agol/"
    "agoldataV2.csv"
)


@register(
    test_id="current-mb-floodinfo",
    category="current",
    source_id="SRC-MB-FLOODINFO",
    label="Manitoba FloodInfo Forecast Centre AGOL CSV (level/flow/forecast)",
    jurisdiction="MB",
    licence="Manitoba Open Government Licence (OpenMB)",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_mb_floodinfo(spec, ctx: ProbeContext) -> TestResult:
    url = MB_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category)
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            fields = fields_from_csv(f.text)
            lines = [ln for ln in f.text.splitlines() if ln.strip()]
            rows = lines[1:] if len(lines) > 1 else []
        except Exception as exc:
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800],
                requests=recs,
            )
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(rows),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="AGOL forecast-centre feed; fields incl measuredFlow/"
                  "measuredLevel/forecastedFlow/floodStage/alert; units feet+cfs",
            extra={"units": "feet + cfs"},
        )


# ── (b) Ontario MNRF Surface Water Monitoring Centre KiWIS ──────────────
ON_URL = (
    "https://www.swmc.mnr.gov.on.ca/KiWIS/KiWIS?service=kisters"
    "&type=queryServices&request=getStationList&datasource=0&format=json"
)


@register(
    test_id="stations-on-kiwis",
    category="stations",
    source_id="SRC-ON-KIWIS",
    label="Ontario SWMC KiWIS getStationList (JSON)",
    jurisdiction="ON",
    licence="Open Government Licence – Ontario",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_on_kiwis(spec, ctx: ProbeContext) -> TestResult:
    url = ON_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category)
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
            # KiWIS getStationList returns a JSON array whose FIRST element is
            # the column-header array; remaining elements are station rows.
            if isinstance(data, list) and data and isinstance(data[0], list):
                fields = [str(c) for c in data[0]]
                rows = data[1:]
                station_count = len(rows)
            else:
                # error object or unexpected shape (e.g. {"type":"error",...})
                fields = fields_from_json(data)
                rows = []
                station_count = None
        except Exception as exc:
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800],
                requests=recs,
            )
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(rows),
            station_count=station_count, latency_ms=f.record.latency_ms,
            sample=f.text[:800], requests=recs,
            notes="first JSON row is the column header; station rows follow",
            extra={},
        )


# ── (c) Québec Vigilance WFS GeoJSON ────────────────────────────────────
QC_URL = "https://geoegl.msp.gouv.qc.ca/apis/mapserver-vigilance/ws/vigilance.fcgi"
QC_PARAMS = {
    "service": "wfs",
    "version": "1.1.0",
    "request": "getfeature",
    "typename": "stations_igo2_public",
    "outputformat": "geojson",
    "srsName": "epsg:4326",
    "maxfeatures": "50",
}


@register(
    test_id="current-qc-vigilance",
    category="current",
    source_id="SRC-QC-VIGILANCE",
    label="Québec Vigilance WFS hydrometric stations (GeoJSON)",
    jurisdiction="QC",
    licence="CC-BY 4.0 (Québec)",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_qc_vigilance(spec, ctx: ProbeContext) -> TestResult:
    url = QC_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, params=QC_PARAMS)
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            data = f.json()
            fields = fields_from_json(data)
            feats = data.get("features", []) if isinstance(data, dict) else []
            n = len(feats)
        except Exception as exc:
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800],
                requests=recs,
            )
        f.record.records_parsed = n
        reason = classify.OK if n else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(n), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=n, station_count=n,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="maxfeatures=50 sample; props incl dern_valeur_niv/"
                  "dern_valeur_deb (latest level/flow)",
            extra={"typename": QC_PARAMS["typename"]},
        )


# ── (d) Newfoundland & Labrador ADRS per-station CSV ────────────────────
NL_URL = "https://www.mae.gov.nl.ca/wrmd/adrs/v6/Data/02YL008_Line.csv"


@register(
    test_id="current-nl-adrs",
    category="current",
    source_id="SRC-NL-ADRS",
    label="Newfoundland & Labrador ADRS per-station CSV (level/flow/temp)",
    jurisdiction="NL",
    licence="Open Government Licence – Newfoundland and Labrador",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_nl_adrs(spec, ctx: ProbeContext) -> TestResult:
    url = NL_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        # URL is a documented per-station file, but the station id came from the
        # upstream ADRS listing → mark as metadata so a 404 reads as an upstream
        # gap, not a path bug on our side.
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, from_metadata=True)
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
            )
        try:
            fields = fields_from_csv(f.text)
            lines = [ln for ln in f.text.splitlines() if ln.strip()]
            rows = lines[1:] if len(lines) > 1 else []
        except Exception as exc:
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800],
                requests=recs,
            )
        f.record.records_parsed = len(rows)
        reason = classify.OK if rows else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(rows), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=len(rows), station_count=1,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="single-station line file (02YL008); header "
                  "STAT_NUM,WSC_NUM,NST_DATI,WATER_TEMP,STAGE,FLOW,BATT_VOLTAGE "
                  "— WATER_TEMP present",
            extra={"example_station": "02YL008"},
        )


# ── (e) Alberta River Basins — discovery (connection-refusing) ──────────
AB_URL = "https://rivers.alberta.ca/DataService/ListStationsAndAlerts"


@register(
    test_id="current-ab-rivers",
    category="current",
    source_id="SRC-AB-RIVERS",
    label="Alberta River Basins ListStationsAndAlerts (discovery)",
    jurisdiction="AB",
    licence="Government of Alberta copyright (non-commercial)",
    commercial_ok="non-commercial",
    sanctioned=False,
)
async def probe_ab_rivers(spec, ctx: ProbeContext) -> TestResult:
    url = AB_URL
    recs = []
    # Short connect timeout so the expected connection refusal surfaces fast
    # rather than hanging on the full read timeout.
    async with build_client(timeout=ctx.request_timeout,
                            connect_timeout=8.0) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category,
                             notes="host commonly refuses non-browser clients")
        recs.append(f.record)
        note = ("per-station static JSON + porExtracts CSV downstream; "
                "rivers.alberta.ca commonly refuses non-browser clients "
                "(connect_refused is expected/valid evidence)")
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                notes=note,
            )
        try:
            data = f.json()
            fields = fields_from_json(data)
            if isinstance(data, list):
                n = len(data)
            elif isinstance(data, dict):
                # some AB payloads wrap the list under a key
                lst = next((v for v in data.values() if isinstance(v, list)), None)
                n = len(lst) if lst is not None else None
            else:
                n = None
        except Exception as exc:
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=url, sample=f.text[:800],
                requests=recs, notes=note,
            )
        reason = classify.OK if n else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(n), reason_category=reason, endpoint=url,
            fields_found=fields, record_count=n, station_count=n,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=note, extra={"downstream": "per-station JSON + porExtracts CSV"},
        )


# ── (f) BC AQUARIUS WebPortal — undocumented export (best-effort) ───────
BC_URL = "https://bcmoe-prod.aquaticinformatics.net/Data/Data_List"


@register(
    test_id="current-bc-aquarius",
    category="current",
    source_id="SRC-BC-AQUARIUS",
    label="BC ENV AQUARIUS WebPortal export (undocumented, best-effort)",
    jurisdiction="BC",
    licence="Open Government Licence – British Columbia",
    commercial_ok="yes",
    sanctioned=False,
)
async def probe_bc_aquarius(spec, ctx: ProbeContext) -> TestResult:
    url = BC_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        # from_metadata: this export path is undocumented/advertised only via the
        # site, so a 404 reads as an upstream gap rather than a constructed-path bug.
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, from_metadata=True,
                             notes="undocumented AQUARIUS WebPortal export")
        recs.append(f.record)
        note = ("undocumented AQUARIUS WebPortal; export/JSON not officially "
                "published — best-effort probe of /Data/Data_List")
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                notes=note,
            )
        # Could be JSON (export) or HTML (portal shell). Try JSON, fall back to
        # HTML with no structured fields — either way never raise.
        fields: list[str] = []
        n = None
        ctype = ""
        if f.response is not None:
            ctype = f.response.headers.get("Content-Type", "")
        try:
            if "json" in ctype.lower():
                data = f.json()
                fields = fields_from_json(data)
                if isinstance(data, list):
                    n = len(data)
                elif isinstance(data, dict):
                    lst = next((v for v in data.values() if isinstance(v, list)), None)
                    n = len(lst) if lst is not None else None
        except Exception:
            fields = []  # HTML/unparseable payload; keep the run alive
        reason = classify.OK if fields else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=url,
            fields_found=fields, record_count=n,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=note, extra={"content_type": ctype},
        )


# ── (g) Saskatchewan WSA hydrographs — scrape-only page (best-effort) ───
SK_URL = "https://www.wsask.ca/hydrographs/05MB006-hrly.html"


@register(
    test_id="current-sk-wsa",
    category="current",
    source_id="SRC-SK-WSA",
    label="Saskatchewan WSA hydrograph page (dygraphs htmlwidget, scrape-only)",
    jurisdiction="SK",
    licence="Saskatchewan Crown copyright",
    commercial_ok="no-written-permission",
    sanctioned=False,
)
async def probe_sk_wsa(spec, ctx: ProbeContext) -> TestResult:
    url = SK_URL
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category,
                             notes="values embedded in dygraphs htmlwidget")
        recs.append(f.record)
        note = ("values are scrape-only: level/flow live inside an embedded "
                "dygraphs htmlwidget (no machine-readable data endpoint)")
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                notes=note,
            )
        # HTML page — no structured field inventory. Signal presence of the
        # htmlwidget payload as weak evidence the data is embedded here.
        has_widget = ("dygraph" in f.text.lower()
                      or "htmlwidget" in f.text.lower())
        return spec.result(
            retrievable=True, reason_category=classify.OK_EMPTY, endpoint=url,
            fields_found=[], record_count=None,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=note,
            extra={"htmlwidget_detected": has_widget,
                   "example_station": "05MB006"},
        )
