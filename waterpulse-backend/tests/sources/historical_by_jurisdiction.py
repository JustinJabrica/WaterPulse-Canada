"""
Historical daily-means, one probe per province/territory (the >=15 historical
requirement: 13 P/T + ECCC national [hydat.py] + weather [below]).

For each P/T the recommended historical source is the federal ECCC archive
(HYDAT / GeoMet hydrometric-daily-mean) — only AB/QC/NL publish a provincial
period-of-record archive, and those are exercised in provincial_hydro.py. Here
we measure each jurisdiction's *real* historical depth via GeoMet daily-mean:
  1. find one station in the province (hydrometric-stations, PROV filter),
  2. query its oldest + newest daily-mean row (sortby DATE / -DATE) → year span.

Plus a weather-historical probe against the Open-Meteo Archive API (ERA5).

Licence: OGL-Canada / ECCC End-use Licence v2.1.1 (ECCC) — commercial OK.
"""
from __future__ import annotations

from tests.sources._base import (ProbeContext, fields_from_json, http_probe,
                                  register, year_span)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

STATIONS_URL = "https://api.weather.gc.ca/collections/hydrometric-stations/items"
DAILY_URL = "https://api.weather.gc.ca/collections/hydrometric-daily-mean/items"
PROVINCES = ["AB", "BC", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "YT", "NT", "NU"]


def _year(fjson) -> int | None:
    feats = (fjson or {}).get("features") or []
    if not feats:
        return None
    p = feats[0].get("properties", {}) or {}
    d = p.get("DATE") or p.get("date") or ""
    if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
        return int(d[:4])
    y = p.get("YEAR")
    try:
        return int(y) if y is not None else None
    except (TypeError, ValueError):
        return None


async def _probe_pt(spec, ctx: ProbeContext) -> TestResult:
    prov = spec.jurisdiction
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        # 1) a station in this province
        s = await http_probe(ctx, client, STATIONS_URL, source_id=spec.source_id,
                             category=spec.category,
                             params={"f": "json", "limit": 1, "PROV_TERR_STATE_LOC": prov})
        recs.append(s.record)
        if not s.ok:
            return spec.result(retrievable=False, reason_category=s.record.reason_category,
                               reason_detail=s.record.reason_detail, endpoint=STATIONS_URL,
                               requests=recs)
        feats = (s.json() or {}).get("features") or []
        if not feats:
            return spec.result(retrievable=False, reason_category=classify.OK_EMPTY,
                               reason_detail=f"no stations for {prov}", endpoint=STATIONS_URL,
                               requests=recs)
        sn = feats[0].get("properties", {}).get("STATION_NUMBER")

        # 2) oldest + newest daily-mean row for that station
        base = {"f": "json", "limit": 1, "STATION_NUMBER": sn}
        old = await http_probe(ctx, client, DAILY_URL, source_id=spec.source_id,
                               category=spec.category, params={**base, "sortby": "DATE"})
        new = await http_probe(ctx, client, DAILY_URL, source_id=spec.source_id,
                               category=spec.category, params={**base, "sortby": "-DATE"})
        recs += [old.record, new.record]
        if not (old.ok or new.ok):
            return spec.result(retrievable=False, reason_category=old.record.reason_category,
                               reason_detail=f"station {sn}: {old.record.reason_detail}",
                               endpoint=DAILY_URL, requests=recs,
                               extra={"sample_station": sn})
        yr_old, yr_new = _year(old.json()), _year(new.json())
        lo, hi, span = year_span([y for y in (yr_old, yr_new) if y is not None])
        fields = fields_from_json(old.json() if old.ok else new.json())
        return spec.result(
            retrievable=True, reason_category=classify.OK if fields else classify.OK_EMPTY,
            endpoint=DAILY_URL, fields_found=fields, station_count=1,
            earliest_year=lo, latest_year=hi, span_years=span,
            latency_ms=old.record.latency_ms,
            sample=(old.text or new.text)[:800], requests=recs,
            notes=f"{prov}: daily-mean depth via ECCC GeoMet, sample station {sn}",
            extra={"sample_station": sn},
        )


async def _probe_weather_archive(spec, ctx: ProbeContext) -> TestResult:
    """Open-Meteo Archive (ERA5) — historical daily weather back to 1940."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 51.05, "longitude": -114.07,
        "start_date": "1940-01-01", "end_date": "1940-01-31",
        "daily": "temperature_2m_mean,precipitation_sum", "timezone": "UTC",
    }
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(ctx, client, url, source_id=spec.source_id,
                             category=spec.category, params=params)
        recs.append(f.record)
        if not f.ok:
            return spec.result(retrievable=False, reason_category=f.record.reason_category,
                               reason_detail=f.record.reason_detail, endpoint=url, requests=recs)
        data = f.json() or {}
        daily = data.get("daily", {})
        fields = ["daily:" + k for k in daily.keys()]
        dates = daily.get("time", [])
        lo = int(dates[0][:4]) if dates else None
        return spec.result(
            retrievable=bool(daily), reason_category=classify.OK if daily else classify.OK_EMPTY,
            endpoint=url, fields_found=fields, record_count=len(dates),
            earliest_year=lo, latest_year=lo, span_years=1 if lo else None,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="ERA5 reanalysis; archive reaches back to 1940 (probed a 1940 window)",
        )


for _prov in PROVINCES:
    register(
        test_id=f"historical-bypt-{_prov.lower()}",
        category="historical",
        source_id="SRC-ECCC-GEOMET-DAILY",
        label=f"ECCC daily-mean historical depth ({_prov})",
        jurisdiction=_prov,
        licence="OGL-Canada / ECCC End-use Licence v2.1.1",
        commercial_ok="yes",
    )(_probe_pt)

register(
    test_id="historical-weather-openmeteo-archive",
    category="historical",
    source_id="SRC-OPEN-METEO-ARCHIVE",
    label="Open-Meteo Archive (ERA5) historical daily weather",
    jurisdiction="multi",
    licence="CC-BY-4.0",
    commercial_ok="non-commercial",
)(_probe_weather_archive)
