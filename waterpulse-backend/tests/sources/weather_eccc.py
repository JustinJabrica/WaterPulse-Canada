"""
ECCC City Page Weather (forecast + current conditions) via MSC Datamart.

The sanctioned, bulk, all-cities weather feed published by Environment and
Climate Change Canada on the MSC Datamart (dd.weather.gc.ca). It is the
public-good replacement for scraping weather.gc.ca city pages and the ECCC
counterpart to Open-Meteo for the app's "weather" panel.

Endpoints (current `/today/` datamart layout, confirmed 2026-09):
  - Site catalogue (all cities):
      https://dd.weather.gc.ca/today/citypage_weather/docs/site_list_en.csv
      columns: Codes, English Names, Province Codes, Latitude, Longitude
  - Per-city current-conditions + forecast XML. There is NO stable
    `xml/{PROV}/{SITECODE}_e.xml` path any more (that legacy path 404s). Files
    now live under an hour-partitioned, timestamp-named tree:
      https://dd.weather.gc.ca/today/citypage_weather/{PROV}/{HH}/
        {YYYYMMDD}T{HHmmss.sss}Z_MSC_CitypageWeather_{SITECODE}_en.xml
    so a city XML is discovered exactly like HYDAT: list the province dir to
    find the latest UTC-hour subdir, list that subdir to find the site's file,
    then fetch it (<= 3 small requests). Parsed with xml.etree.ElementTree.

Licence: Open Government Licence - Canada (OGL-Canada) / ECCC Data Servers
End-use Licence v2.1.1 (commercial OK; attribution "Data Source: Environment
and Climate Change Canada"). Citation / docs:
  https://eccc-msc.github.io/open-data/msc-data/citypage-weather/readme_citypageweather-datamart_en/

Policy: low-load, read-only; no cache-bypass headers; contact MSC only above
~86,400 req/day. This module issues 1 request for the site list and <= 3 for
one sample city (Calgary, AB / s0000047).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from tests.sources._base import ProbeContext, fields_from_csv, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

DATAMART = "https://dd.weather.gc.ca/today/citypage_weather"
SITE_LIST_URL = f"{DATAMART}/docs/site_list_en.csv"

# One representative city used for the XML field-inventory probe.
SAMPLE_PROV = "AB"
SAMPLE_SITE = "s0000047"   # Calgary (from site_list_en.csv)
SAMPLE_CITY = "Calgary"

# Advertised site-catalogue columns.
SITE_LIST_COLUMNS = ["Codes", "English Names", "Province Codes", "Latitude", "Longitude"]

# The app's Open-Meteo weather panel consumes this field set. We report, for
# the ECCC City Page feed, which of these are PRESENT vs MISSING.
OPEN_METEO_FIELDS = [
    "apparent_temperature",       # feels-like
    "uv_index",
    "visibility",
    "wind_gusts",
    "precipitation_probability",
    "is_day",
]

# Regexes over the MSC Datamart Apache-style autoindex HTML.
_HOUR_RE = re.compile(r'href="(\d{2})/"')


def _site_file_re(site: str) -> re.Pattern:
    return re.compile(
        r'href="([^"]*_MSC_CitypageWeather_' + re.escape(site) + r'_en\.xml)"'
    )


# ── Probe 1: the all-cities site catalogue CSV ──────────────────────
@register(
    test_id="weather-eccc-citypage-sitelist",
    category="weather",
    source_id="SRC-ECCC-CITYPAGE",
    label="ECCC City Page Weather - site catalogue CSV (all cities)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC End-use Licence v2.1.1",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_site_list(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, SITE_LIST_URL, source_id=spec.source_id,
            category=spec.category, notes="site catalogue CSV",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=SITE_LIST_URL,
                requests=recs,
            )
        fields = fields_from_csv(f.text)
        lines = [ln for ln in f.text.splitlines() if ln.strip()]
        data = lines[1:] if len(lines) > 1 else []
        f.record.records_parsed = len(data)
        reason = classify.OK if data else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(data), reason_category=reason, endpoint=SITE_LIST_URL,
            fields_found=fields, record_count=len(data), station_count=len(data),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="site catalogue: siteCode,name,province,lat,lon; one row per city",
            extra={"expected_columns": SITE_LIST_COLUMNS},
        )


# ── Probe 2: one city XML → current-conditions field inventory ──────
@register(
    test_id="weather-eccc-citypage-ab",
    category="weather",
    source_id="SRC-ECCC-CITYPAGE",
    label=f"ECCC City Page Weather - city XML ({SAMPLE_CITY}, {SAMPLE_PROV})",
    jurisdiction=SAMPLE_PROV,
    licence="OGL-Canada / ECCC End-use Licence v2.1.1",
    commercial_ok="yes",
    sanctioned=True,
)
async def probe_city_xml(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    prov_url = f"{DATAMART}/{SAMPLE_PROV}/"
    async with build_client(timeout=ctx.request_timeout) as client:
        # 1) list the province dir → find the latest UTC-hour subdir
        d = await http_probe(
            ctx, client, prov_url, source_id=spec.source_id,
            category=spec.category, notes="province dir listing",
        )
        recs.append(d.record)
        if not d.ok:
            return spec.result(
                retrievable=False, reason_category=d.record.reason_category,
                reason_detail=d.record.reason_detail, endpoint=prov_url, requests=recs,
            )
        hours = sorted(set(_HOUR_RE.findall(d.text)))
        if not hours:
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail="no HH subdirs in province listing",
                endpoint=prov_url, sample=d.text[:800], requests=recs,
            )
        hour = hours[-1]
        hour_url = f"{DATAMART}/{SAMPLE_PROV}/{hour}/"

        # 2) list the hour dir → find this site's timestamped file
        h = await http_probe(
            ctx, client, hour_url, source_id=spec.source_id, category=spec.category,
            from_metadata=True, notes="hour dir listing",
        )
        recs.append(h.record)
        if not h.ok:
            return spec.result(
                retrievable=False, reason_category=h.record.reason_category,
                reason_detail=h.record.reason_detail, endpoint=hour_url, requests=recs,
            )
        files = _site_file_re(SAMPLE_SITE).findall(h.text)
        if not files:
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=f"{SAMPLE_SITE} not found in {hour_url}",
                endpoint=hour_url, sample=h.text[:800], requests=recs,
            )
        xml_url = urljoin(hour_url, sorted(files)[-1])

        # 3) fetch the city XML
        x = await http_probe(
            ctx, client, xml_url, source_id=spec.source_id, category=spec.category,
            from_metadata=True, notes="city current-conditions XML",
        )
        recs.append(x.record)
        if not x.ok:
            return spec.result(
                retrievable=False, reason_category=x.record.reason_category,
                reason_detail=x.record.reason_detail, endpoint=xml_url, requests=recs,
            )

        # 4) parse + inventory (never raise for logic bugs → PARSE_ERROR)
        try:
            return _inventory(spec, xml_url, x, recs, hour)
        except Exception as exc:  # keep the run alive
            _reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=xml_url, sample=x.text[:800],
                requests=recs,
            )


def _inventory(spec, xml_url, x, recs, hour) -> TestResult:
    root = ET.fromstring(x.text)  # ET.ParseError caught by caller

    cc = root.find("currentConditions")
    cc_tags = [child.tag for child in cc] if cc is not None else []
    wind = cc.find("wind") if cc is not None else None
    wind_tags = [child.tag for child in wind] if wind is not None else []

    def cc_has(tag: str) -> bool:
        return cc is not None and cc.find(tag) is not None

    def wind_has(tag: str) -> bool:
        return wind is not None and wind.find(tag) is not None

    # Forecast-level signals (UV index / probability of precipitation live in
    # <forecastGroup>, not in currentConditions).
    uv_present = next(root.iter("uv"), None) is not None
    pop_present = next(root.iter("pop"), None) is not None
    # ECCC's closest "feels-like" analogues are windChill / humidex.
    feels_present = cc_has("windChill") or cc_has("humidex")

    # fields_found = currentConditions child tags + a marker per app-required
    # field that is actually present.
    markers = []
    if cc_has("temperature"):
        markers.append("req:temperature")
    if cc_has("dewpoint"):
        markers.append("req:dewpoint")
    if cc_has("relativeHumidity"):
        markers.append("req:humidity(relativeHumidity)")
    if wind_has("speed"):
        markers.append("req:wind.speed")
    if wind_has("gust"):
        markers.append("req:wind.gust")
    if wind_has("direction"):
        markers.append("req:wind.direction")
    if cc_has("pressure"):
        markers.append("req:pressure")
    if cc_has("visibility"):
        markers.append("req:visibility")
    if uv_present:
        markers.append("req:forecast.uv_index")
    fields = cc_tags + markers

    # Open-Meteo panel comparison: present vs missing.
    comparison = {
        "apparent_temperature": feels_present,     # ECCC windChill/humidex proxy
        "uv_index": uv_present,                     # ECCC: forecast-only
        "visibility": cc_has("visibility"),
        "wind_gusts": wind_has("gust"),
        "precipitation_probability": pop_present,   # ECCC: forecast-only (pop)
        "is_day": False,                            # ECCC has no is_day field
    }
    present = [k for k in OPEN_METEO_FIELDS if comparison[k]]
    missing = [k for k in OPEN_METEO_FIELDS if not comparison[k]]

    reason = classify.OK if cc_tags else classify.OK_EMPTY
    x.record.records_parsed = len(cc_tags)

    notes = (
        f"{SAMPLE_CITY} {SAMPLE_SITE}; MISSING vs Open-Meteo set: "
        f"{', '.join(missing) if missing else 'none'}. "
        "uv_index & precipitation_probability are forecast-only in ECCC (not in "
        "currentConditions); is_day is absent; apparent_temperature only via "
        "windChill/humidex."
    )
    return spec.result(
        retrievable=True, reason_category=reason, endpoint=xml_url,
        fields_found=fields, record_count=len(cc_tags), station_count=1,
        latency_ms=x.record.latency_ms, sample=x.text[:800], requests=recs,
        notes=notes,
        extra={
            "current_conditions_tags": cc_tags,
            "wind_tags": wind_tags,
            "app_required_present": markers,
            "open_meteo_present": present,
            "open_meteo_missing": missing,
            "open_meteo_comparison": comparison,
            "discovered_url": xml_url,
            "hour_dir": hour,
        },
    )
