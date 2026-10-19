"""
Snow — snow water equivalent (SWE) & snow depth sources (category="snow").

Three probes:

(a) CanSWE (SRC-CANSWE) — the Canadian historical Snow Water Equivalent
    dataset (CanSWE / CanEEN), a national, quality-controlled compilation of
    manual snow-course + automatic snow-pillow SWE and depth back to 1928.
    Published on Zenodo (versioned DOI); the record JSON *is* the metadata, so
    this probe is metadata-only and NEVER downloads the ~14 MB NetCDF / zip.
      API record: https://zenodo.org/api/records/19075529  (JSON)
      Landing:    https://doi.org/10.5281/zenodo.19075529
      Licence:    OGL-Canada (Zenodo licence id "canada-crown"), commercial OK.
      Citation:   Vionnet et al., CanSWE, ESSD (2021), updated annually.

(b) BC ASWS (SRC-BC-ASWS) — BC Automated Snow Weather Stations, near-real-time.
    Single wide CSV: a Date/time column followed by one column per station
    (station-id headers), so station_count = header columns after the date.
      SWE:   https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data/SW.csv
      Siblings at the same path: SD.csv (snow depth), PC.csv (accumulated
      precip), TA.csv (air temp).
      Licence: Open Government Licence – British Columbia, commercial OK.

(c) AB snow pillows (SRC-AB-SNOW) — Alberta River Basins (rivers.alberta.ca)
    snow-pillow SWE/depth network (~16 pillows). No stable documented flat-file
    endpoint; data is served through a dynamic app handler and the host is
    bot-touchy / prone to connection refusal. Marked sanctioned=False so
    probe_sources skips it — it runs only in the user-launched residual harness.
      Site: https://rivers.alberta.ca/
      Licence: Open Government Licence – Alberta (terms-of-use unconfirmed).
"""
from __future__ import annotations

import re

from tests.sources._base import (
    ProbeContext,
    fields_from_csv,
    http_probe,
    register,
    year_span,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── (a) CanSWE via Zenodo ───────────────────────────────────────────
CANSWE_URL = "https://zenodo.org/api/records/19075529"


@register(
    test_id="snow-canswe-zenodo-ca",
    category="snow",
    source_id="SRC-CANSWE",
    label="CanSWE national SWE dataset (Zenodo record metadata)",
    jurisdiction="CA",
    licence="OGL-Canada (Zenodo canada-crown)",
    commercial_ok="yes",
)
async def probe_canswe(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, CANSWE_URL, source_id=spec.source_id,
                             category=spec.category, notes="Zenodo record (metadata-only)")
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=CANSWE_URL, requests=recs,
            )
        try:
            data = f.json()
            meta = data.get("metadata", {}) if isinstance(data, dict) else {}
            files = data.get("files", []) if isinstance(data, dict) else []
            if not isinstance(files, list):
                files = []
            title = meta.get("title", "") if isinstance(meta, dict) else ""
            lic = meta.get("license") if isinstance(meta, dict) else None
            if isinstance(lic, dict):
                lic_str = lic.get("id") or lic.get("title") or str(lic)
            else:
                lic_str = str(lic) if lic is not None else ""

            # Distinct keys across the file objects → field inventory.
            file_keys: list[str] = []
            file_list: list[dict] = []
            for fl in files:
                if not isinstance(fl, dict):
                    continue
                for k in fl.keys():
                    if k not in file_keys:
                        file_keys.append(k)
                file_list.append({"name": fl.get("key"), "size": fl.get("size")})

            fields = ["files", "metadata.title", "metadata.license"] + [
                f"files[].{k}" for k in file_keys
            ]

            # Year span is embedded in the title, e.g. "CanSWE, 1928-2025".
            yrs = re.findall(r"(?:19|20)\d{2}", title)
            lo, hi, span = year_span(yrs)

            f.record.records_parsed = len(files)
            reason = classify.OK if files else classify.OK_EMPTY
            return spec.result(
                retrievable=True, reason_category=reason, endpoint=CANSWE_URL,
                fields_found=fields, record_count=len(files),
                earliest_year=lo, latest_year=hi, span_years=span,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes=f"metadata-only (NetCDF/zip NOT downloaded); title={title!r}",
                extra={"title": title, "license": lic_str,
                       "doi": data.get("doi") if isinstance(data, dict) else None,
                       "files": file_list},
            )
        except Exception as exc:  # parsing only — HTTP already classified
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=CANSWE_URL, sample=f.text[:800],
                latency_ms=f.record.latency_ms, requests=recs,
            )


# ── (b) BC Automated Snow Weather Stations (near-real-time wide CSVs) ─
BC_ASWS_BASE = "https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data"
# One wide CSV per parameter (col 0 = date/time; each later col = a station).
# SW/SD feed the "snow" category; PC → precip; TA → weather — one network, four
# environmental variables, so all four are probed for full coverage.
_ASWS_FILES = [
    ("SW", "snow", "SWE (snow water equivalent)"),
    ("SD", "snow", "snow depth"),
    ("PC", "precip", "accumulated precipitation"),
    ("TA", "weather", "air temperature"),
]


def _make_asws(code: str, desc: str):
    async def _probe(spec, ctx: ProbeContext) -> TestResult:
        url = f"{BC_ASWS_BASE}/{code}.csv"
        recs = []
        async with build_client(timeout=ctx.request_timeout) as client:
            f = await http_probe(ctx, client, url, source_id=spec.source_id,
                                 category=spec.category, notes=f"ASWS {code}.csv wide CSV")
            recs.append(f.record)
            if not f.ok:
                return spec.result(
                    retrievable=False, reason_category=f.record.reason_category,
                    reason_detail=f.record.reason_detail, endpoint=url, requests=recs,
                )
            try:
                fields = fields_from_csv(f.text)
                lines = [ln for ln in f.text.splitlines() if ln.strip()]
                data = lines[1:] if len(lines) > 1 else []
                # col 0 = date/time; every later column is a station.
                station_count = max(0, len(fields) - 1)
                f.record.records_parsed = len(data)
                reason = classify.OK if data else classify.OK_EMPTY
                return spec.result(
                    retrievable=bool(data), reason_category=reason, endpoint=url,
                    fields_found=fields, record_count=len(data), station_count=station_count,
                    latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                    notes=f"BC ASWS {desc}: wide CSV, col 0 = date, each later col = a station",
                    extra={"parameter": code, "columns_after_date_are_stations": True},
                )
            except Exception as exc:  # parsing only
                _, detail = classify.classify_exception(exc)
                return spec.result(
                    retrievable=False, reason_category=classify.PARSE_ERROR,
                    reason_detail=detail, endpoint=url, sample=f.text[:800],
                    latency_ms=f.record.latency_ms, requests=recs,
                )
    return _probe


for _code, _cat, _desc in _ASWS_FILES:
    register(
        test_id=f"{_cat}-bc-asws-{_code.lower()}",
        category=_cat,
        source_id="SRC-BC-ASWS",
        label=f"BC ASWS {_desc} (wide CSV)",
        jurisdiction="BC",
        licence="Open Government Licence – British Columbia",
        commercial_ok="yes",
    )(_make_asws(_code, _desc))


# ── (c) Alberta River Basins snow pillows (residual, sanctioned=False) ──
AB_SNOW_URL = "https://rivers.alberta.ca/"


@register(
    test_id="snow-ab-pillows-residual",
    category="snow",
    source_id="SRC-AB-SNOW",
    label="Alberta River Basins snow pillows (residual)",
    jurisdiction="AB",
    licence="Open Government Licence – Alberta (unconfirmed)",
    commercial_ok="unknown",
    sanctioned=False,
)
async def probe_ab_snow(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, AB_SNOW_URL, source_id=spec.source_id,
                             category=spec.category, notes="residual: bot-touchy AB host")
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=AB_SNOW_URL, requests=recs,
                notes=("residual (sanctioned=False): rivers.alberta.ca is bot-touchy / "
                       "connection-refusing and has no documented flat-file snow-pillow "
                       "endpoint; runs only in the user-launched residual harness"),
            )
        # If it unexpectedly responds, do a best-effort field sniff.
        fields = fields_from_csv(f.text) if "," in f.text else []
        reason = classify.OK if fields else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=AB_SNOW_URL,
            fields_found=fields, latency_ms=f.record.latency_ms,
            sample=f.text[:800], requests=recs,
            notes="residual (sanctioned=False): landing responded; snow-pillow data "
                  "is served via a dynamic app handler, not this URL",
            extra={"residual": True},
        )
