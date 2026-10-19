"""
Open-Meteo Forecast API — the app's live weather + forecast provider.

WaterPulse pulls per-station current conditions and a 7-day daily forecast from
Open-Meteo's free forecast endpoint (no API key, ~10k calls/day free tier). This
probe mirrors the app's EXACT variable set (see
``app/services/weather.py`` :data:`CURRENT_VARIABLES` / :data:`DAILY_VARIABLES`)
against a single Calgary coordinate to prove the full weather contract the UI
depends on is retrievable from this source.

Endpoint:
  GET https://api.open-meteo.com/v1/forecast
  params: latitude, longitude, current=<11 vars>, daily=<13 vars>,
          forecast_days=7, timezone=America/Edmonton, plus the unit params the
          app sends (wind_speed_unit=kmh, temperature_unit=celsius,
          precipitation_unit=mm).

Response is a single JSON object with ``current`` (dict of scalar values) and
``daily`` (dict of arrays, one per forecast day). fields_found is reported as the
keys of ``current`` plus ``daily:<key>`` for each daily variable, so Report 3 can
confirm every app-required variable is present.

Licence: CC-BY-4.0 (attribution "Weather data by Open-Meteo.com"). Non-commercial
use only on the free tier; commercial use requires a paid Open-Meteo subscription.
Citation / terms: https://open-meteo.com/en/license
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, http_probe, register, year_span
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Calgary (Bow River) — a representative Canadian coordinate.
LATITUDE = 51.05
LONGITUDE = -114.07

# Mirror of app/services/weather.py CURRENT_VARIABLES (the exact current-weather
# contract the frontend renders).
CURRENT_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "visibility",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "uv_index",
    "is_day",
]

# Mirror of app/services/weather.py DAILY_VARIABLES (the exact 7-day forecast
# contract). Includes visibility_mean, which the app requests for daily views.
DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "sunrise",
    "sunset",
    "uv_index_max",
    "visibility_mean",
]

PARAMS = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "current": ",".join(CURRENT_VARIABLES),
    "daily": ",".join(DAILY_VARIABLES),
    "forecast_days": 7,
    "timezone": "America/Edmonton",
    # Unit params the app sends so the response shape matches production exactly.
    "wind_speed_unit": "kmh",
    "temperature_unit": "celsius",
    "precipitation_unit": "mm",
}


async def _probe(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, FORECAST_URL, source_id=spec.source_id,
            category=spec.category, params=PARAMS, from_metadata=False,
            notes="single-coord forecast (current + 7-day daily)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=FORECAST_URL,
                requests=recs,
            )

        try:
            data = f.json()
            current = data.get("current", {}) if isinstance(data, dict) else {}
            daily = data.get("daily", {}) if isinstance(data, dict) else {}
            if not isinstance(current, dict):
                current = {}
            if not isinstance(daily, dict):
                daily = {}

            # fields_found = keys of current + ("daily:" + k) for each daily key.
            fields = list(current.keys()) + [f"daily:{k}" for k in daily.keys()]

            # Daily arrays are keyed by "time"; use it for record count + span.
            times = daily.get("time") or []
            record_count = len(times) if isinstance(times, list) else None
            years = []
            if isinstance(times, list):
                for t in times:
                    s = str(t)
                    if len(s) >= 4 and s[:4].isdigit():
                        years.append(int(s[:4]))
            lo, hi, span = year_span(years)

            # Prove the full app contract: which required variables are present?
            missing_current = [v for v in CURRENT_VARIABLES if v not in current]
            missing_daily = [v for v in DAILY_VARIABLES if v not in daily]
            full_coverage = not missing_current and not missing_daily
        except Exception as exc:  # noqa: BLE001 — never let a parse bug abort the run
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False,
                reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=FORECAST_URL,
                latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
                notes="failed to parse Open-Meteo forecast JSON",
            )

        f.record.records_parsed = record_count or 0
        has_data = bool(current) or bool(daily)
        note = (
            "confirms the full app weather contract (current + 7-day daily) is "
            "available here"
        )
        if not full_coverage:
            note = (
                "partial coverage: missing current="
                f"{missing_current} daily={missing_daily}"
            )
        return spec.result(
            retrievable=has_data,
            reason_category=classify.OK if (has_data and fields) else classify.OK_EMPTY,
            endpoint=FORECAST_URL, fields_found=fields,
            record_count=record_count, station_count=1,
            earliest_year=lo, latest_year=hi, span_years=span,
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=note,
            extra={
                "expected_current": CURRENT_VARIABLES,
                "expected_daily": DAILY_VARIABLES,
                "missing_current": missing_current,
                "missing_daily": missing_daily,
                "full_coverage": full_coverage,
                "elevation_m": data.get("elevation") if isinstance(data, dict) else None,
            },
        )


register(
    test_id="weather-openmeteo-forecast-ca",
    category="weather",
    source_id="SRC-OPEN-METEO",
    label="Open-Meteo forecast (current + 7-day daily; app weather contract)",
    jurisdiction="CA",
    licence="CC-BY-4.0",
    commercial_ok="non-commercial",
    sanctioned=True,
)(_probe)
