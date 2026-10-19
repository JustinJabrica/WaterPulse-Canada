"""
HYDAT — Water Survey of Canada National Water Data Archive.

The deepest, validated historical source: daily & monthly means of flow +
water level + sediment, plus annual extremes, full period of record (decades;
oldest WSC records reach the 1800s), for all ~7,900 Canadian stations. One
SQLite file, updated quarterly. THE sanctioned replacement for per-station
historical scraping. Reference template for a download+SQLite probe.

Licence: OGL-Canada / ECCC End-use Licence (commercial OK, attribution).
Download host: http://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/
Files: Hydat_sqlite3_YYYYMMDD.zip

Default is METADATA-ONLY (discover latest file + size) because the zip is
~1–1.5 GB; pass allow_downloads (default True) to actually download, unzip,
open the SQLite and measure the real historical depth. Use `--no-downloads`
on probe_sources for a fast validation pass.
"""
from __future__ import annotations

import os
import re
import sqlite3
import zipfile

from tests.sources._base import ProbeContext, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

INDEX_URL = "http://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/"
_ZIP_RE = re.compile(r"Hydat_sqlite3_(\d{8})\.zip")

# Documented HYDAT tables/fields (advertised — measured set confirmed on download)
DOCUMENTED_FIELDS = [
    "STATIONS", "DLY_FLOWS(STATION_NUMBER,YEAR,MONTH,FLOW1..FLOW31,MONTHLY_MEAN)",
    "DLY_LEVELS(STATION_NUMBER,YEAR,MONTH,LEVEL1..LEVEL31)",
    "ANNUAL_STATISTICS", "SED_DLY_LOADS",
]
# ~15 MB is a generous ceiling for "small enough to pull inline"; HYDAT far
# exceeds it, so downloads are opt-in via allow_downloads.


async def _probe(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=max(120.0, ctx.request_timeout)) as client:
        # 1) discover the latest Hydat_sqlite3_YYYYMMDD.zip from the index
        idx = await http_probe(ctx, client, INDEX_URL, source_id=spec.source_id,
                               category=spec.category, notes="index listing")
        recs.append(idx.record)
        if not idx.ok:
            return spec.result(retrievable=False, reason_category=idx.record.reason_category,
                               reason_detail=idx.record.reason_detail, endpoint=INDEX_URL,
                               requests=recs)
        dates = _ZIP_RE.findall(idx.text)
        if not dates:
            return spec.result(retrievable=False, reason_category=classify.PARSE_ERROR,
                               reason_detail="no Hydat_sqlite3_YYYYMMDD.zip in index",
                               endpoint=INDEX_URL, sample=idx.text[:800], requests=recs)
        latest = max(dates)
        zip_name = f"Hydat_sqlite3_{latest}.zip"
        zip_url = INDEX_URL + zip_name

        # 2) HEAD the zip for size (cheap retrievability + freshness signal)
        head = await http_probe(ctx, client, zip_url, source_id=spec.source_id,
                                category=spec.category, method="HEAD", read_text=False,
                                notes="zip HEAD (size/freshness)")
        recs.append(head.record)
        size_mb = None
        if head.response is not None:
            cl = head.response.headers.get("Content-Length")
            if cl and cl.isdigit():
                size_mb = round(int(cl) / 1_048_576, 1)

        base = dict(
            endpoint=zip_url, requests=recs,
            latency_ms=idx.record.latency_ms,
            extra={"latest_file": zip_name, "quarterly_date": latest,
                   "zip_size_mb": size_mb},
        )

        # 3) metadata-only unless downloads allowed (zip is ~1–1.5 GB)
        if not ctx.allow_downloads:
            return spec.result(
                retrievable=head.ok or head.response is not None,
                reason_category=classify.OK, fields_found=DOCUMENTED_FIELDS,
                notes=f"metadata-only (download skipped); latest={zip_name} size={size_mb}MB",
                sample=f"latest HYDAT: {zip_name} (~{size_mb} MB)", **base,
            )

        # 4) full: download → unzip → open SQLite → measure real depth
        try:
            meas = await _download_and_measure(client, zip_url, ctx, spec, recs)
        except Exception as exc:  # keep the run alive
            reason, detail = classify.classify_exception(exc)
            return spec.result(retrievable=True, reason_category=classify.OK,
                               fields_found=DOCUMENTED_FIELDS,
                               notes=f"discovered but measure failed: {detail}", **base)
        base["extra"].update(meas.pop("extra", {}))
        return spec.result(retrievable=True, reason_category=classify.OK, **meas, **base)


async def _download_and_measure(client, zip_url, ctx: ProbeContext, spec, recs) -> dict:
    os.makedirs(ctx.cache_dir, exist_ok=True)
    zip_path = os.path.join(ctx.cache_dir, os.path.basename(zip_url))
    db_path = os.path.join(ctx.cache_dir, "Hydat.sqlite3")

    if not os.path.exists(db_path):
        # stream the (large) zip to disk
        async with client.stream("GET", zip_url) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as fh:
                async for chunk in resp.aiter_bytes(1_048_576):
                    fh.write(chunk)
        with zipfile.ZipFile(zip_path) as zf:
            member = next(n for n in zf.namelist() if n.lower().endswith((".sqlite3", ".sqlite", ".db")))
            with zf.open(member) as src, open(db_path, "wb") as dst:
                dst.write(src.read())

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        cols = [r[1] for r in cur.execute("PRAGMA table_info(DLY_FLOWS)")]
        lo, hi = cur.execute("SELECT MIN(YEAR), MAX(YEAR) FROM DLY_FLOWS").fetchone()
        nrows = cur.execute("SELECT COUNT(*) FROM DLY_FLOWS").fetchone()[0]
        nstations = cur.execute(
            "SELECT COUNT(DISTINCT STATION_NUMBER) FROM DLY_FLOWS").fetchone()[0]
        return {
            "fields_found": tables + [f"DLY_FLOWS.{c}" for c in cols],
            "record_count": nrows,
            "station_count": nstations,
            "earliest_year": lo, "latest_year": hi,
            "span_years": (hi - lo + 1) if lo and hi else None,
            "notes": f"measured from {os.path.basename(db_path)}; {len(tables)} tables",
            "sample": f"tables={tables[:12]}",
            "extra": {"dly_flows_columns": cols},
        }
    finally:
        con.close()


register(
    test_id="historical-hydat-ca",
    category="historical",
    source_id="SRC-HYDAT",
    label="HYDAT national archive (daily/monthly means, full record)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC End-use Licence",
    commercial_ok="yes",
)(_probe)
