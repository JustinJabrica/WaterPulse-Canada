"""
River / lake ice — ECCC scientific-knowledge datasets + CIS ice thickness.

Three sanctioned, official ECCC sources for the "ice" category. All are
metadata-only here (index reachability + a HEAD on the first data-file link);
no bulk file is downloaded inline.

(a) SRC-CRID — Canadian River Ice Database.
    Index: https://data-donnees.ec.gc.ca/data/water/scientificknowledge/canadian-river-ice-database/
    196 National Hydrometric Program (NHP) sites whose observations join to WSC
    station numbers; period of record 1894-2015 (freeze-up / break-up dates,
    ice-affected flow flags, B-dates).

(b) SRC-LAKEICE — Lake Ice Database.
    Index: https://data-donnees.ec.gc.ca/data/water/scientificknowledge/lake-ice-database/
    Historical lake freeze-up / break-up / ice-cover records.

(c) SRC-CIS-ICE — Canadian Ice Service ice-thickness archive.
    Data page: https://www.canada.ca/en/environment-climate-change/services/
    ice-forecasts-observations/latest-conditions/archive-overview/thickness-data.html
    In-situ ice-thickness & on-ice snow-depth measurements (weekly, historical).

Both data-donnees.ec.gc.ca indexes are directory-style catalogue listings; we
GET the index and regex for a .csv/.zip/.xlsx data-file href, then HEAD the
first match (from_metadata=True — the link is advertised upstream). The listing
is partly JS-rendered, so a static GET may expose no file link; the probe still
reports the index as retrievable and records the miss.

Licence: OGL-Canada (Open Government Licence — Canada); commercial use OK with
attribution "Contains information licensed under the Open Government Licence -
Canada". Citation: https://open.canada.ca/en/open-government-licence-canada
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from tests.sources._base import ProbeContext, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

CRID_INDEX = (
    "https://data-donnees.ec.gc.ca/data/water/scientificknowledge/"
    "canadian-river-ice-database/"
)
LAKEICE_INDEX = (
    "https://data-donnees.ec.gc.ca/data/water/scientificknowledge/"
    "lake-ice-database/"
)
CIS_THICKNESS = (
    "https://www.canada.ca/en/environment-climate-change/services/"
    "ice-forecasts-observations/latest-conditions/archive-overview/"
    "thickness-data.html"
)

# Match an href pointing at a bulk data file (csv/zip/spreadsheet/netCDF/text).
_DATA_RE = re.compile(
    r'href=["\']?([^"\'>\s]+\.(?:csv|zip|xlsx|xls|nc|txt))',
    re.IGNORECASE,
)


async def _probe_index_db(spec, ctx: ProbeContext, index_url: str, notes: str) -> TestResult:
    """GET a data-donnees index; regex for a data-file link; HEAD the first."""
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        idx = await http_probe(
            ctx, client, index_url, source_id=spec.source_id,
            category=spec.category, notes="index listing",
        )
        recs.append(idx.record)
        if not idx.ok:
            return spec.result(
                retrievable=False, reason_category=idx.record.reason_category,
                reason_detail=idx.record.reason_detail, endpoint=index_url,
                requests=recs,
            )

        # Discover candidate bulk data-file links from the listing HTML.
        data_files: list[str] = []
        try:
            seen = set()
            for m in _DATA_RE.finditer(idx.text or ""):
                href = m.group(1)
                if href.lower().startswith(("mailto:", "javascript:", "#")):
                    continue
                absurl = urljoin(index_url, href)
                if absurl not in seen:
                    seen.add(absurl)
                    data_files.append(absurl)
        except Exception as exc:  # index is reachable; only link-parse failed
            _, detail = classify.classify_exception(exc)
            data_files = []
            recs[-1].notes = (recs[-1].notes + f"; link-parse failed: {detail}").strip("; ")

        # HEAD the first candidate for size/freshness (link came from upstream).
        size_mb = None
        first = data_files[0] if data_files else None
        if first:
            head = await http_probe(
                ctx, client, first, source_id=spec.source_id,
                category=spec.category, method="HEAD", read_text=False,
                from_metadata=True, notes="data-file HEAD (size/freshness)",
            )
            recs.append(head.record)
            if head.response is not None:
                cl = head.response.headers.get("Content-Length")
                if cl and cl.isdigit():
                    size_mb = round(int(cl) / 1_048_576, 1)

        reason = classify.OK if data_files else classify.OK_EMPTY
        head_note = f"; first data-file HEAD size={size_mb}MB" if size_mb is not None else ""
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=index_url,
            record_count=(len(data_files) or None),
            latency_ms=idx.record.latency_ms, sample=(idx.text or "")[:800],
            requests=recs,
            notes=(f"{notes} index reachable; {len(data_files)} data-file link(s) "
                   f"found (listing partly JS-rendered)" + head_note),
            extra={
                "data_files": data_files[:20],
                "first_data_file": first,
                "first_data_file_size_mb": size_mb,
            },
        )


# ── (a) Canadian River Ice Database ─────────────────────────────────
@register(
    test_id="ice-crid-ca",
    category="ice",
    source_id="SRC-CRID",
    label="Canadian River Ice Database (NHP sites, freeze/break-up)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_crid(spec, ctx: ProbeContext) -> TestResult:
    res = await _probe_index_db(
        spec, ctx, CRID_INDEX,
        notes="CRID: 196 NHP sites join to WSC station numbers, 1894-2015;",
    )
    # Documented dataset metadata (constant regardless of listing parse).
    res.station_count = 196
    res.earliest_year = 1894
    res.latest_year = 2015
    res.span_years = 2015 - 1894 + 1
    res.extra["documented"] = {
        "nhp_sites": 196, "joins_to": "WSC station_number",
        "period_of_record": "1894-2015",
    }
    return res


# ── (b) Lake Ice Database ───────────────────────────────────────────
@register(
    test_id="ice-lakeice-ca",
    category="ice",
    source_id="SRC-LAKEICE",
    label="Lake Ice Database (freeze-up / break-up / ice cover)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_lakeice(spec, ctx: ProbeContext) -> TestResult:
    return await _probe_index_db(
        spec, ctx, LAKEICE_INDEX,
        notes="Lake Ice DB: historical lake freeze-up/break-up/ice-cover;",
    )


# ── (c) CIS ice-thickness archive ───────────────────────────────────
@register(
    test_id="ice-cis-thickness-ca",
    category="ice",
    source_id="SRC-CIS-ICE",
    label="Canadian Ice Service ice-thickness archive (data page)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_cis_thickness(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, CIS_THICKNESS, source_id=spec.source_id,
            category=spec.category, from_metadata=True,
            notes="CIS ice-thickness data page (retrievability check)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=CIS_THICKNESS,
                requests=recs,
            )
        text = f.text or ""
        reason = classify.OK if text.strip() else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=CIS_THICKNESS,
            latency_ms=f.record.latency_ms, sample=text[:800], requests=recs,
            notes="CIS thickness data page reachable; in-situ ice-thickness + "
                  "on-ice snow-depth archive (metadata-only, no bulk download)",
            extra={"page_bytes": f.record.resp_bytes},
        )
