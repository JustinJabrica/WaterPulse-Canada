"""
compute_percentiles.py

Background job that downloads 365-day historical CSVs from rivers.alberta.ca
and pre-computes percentiles for every day-of-year per station.

Results are saved to percentiles.json for use by RiverFlowsAndLevels.py.

Run this daily or weekly:
    python compute_percentiles.py
"""

import asyncio
import json
from datetime import datetime
from collections import defaultdict

import httpx

STATIONS_FILE = "stations_extracted.json"
OUTPUT_FILE = "percentiles.json"

# Number of header/disclaimer rows to skip in historical CSVs
CSV_HEADER_ROWS = 22

# Days on either side of a target day-of-year for the rolling window
PERCENTILE_WINDOW_DAYS = 7

# Max concurrent CSV downloads (be respectful to the server)
MAX_CONCURRENCY = 10

# Timeout for CSV downloads (some files are 3MB+)
DOWNLOAD_TIMEOUT = 60


def load_stations(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def find_dataset_url(station: dict, keyword: str) -> str | None:
    """Find a dataset URL from the station's datasets by keyword match."""
    datasets = station.get("datasets", [])
    if not datasets:
        return None
    for ds in datasets:
        desc = ds.get("dataset_description", "").lower()
        loc = ds.get("dataset_location", "")
        if keyword.lower() in desc and loc.endswith(".csv"):
            return loc
    return None


def parse_csv_content(text: str) -> list[dict] | None:
    """Parse a historical CSV string into list of {day_of_year, value}."""
    lines = text.splitlines()
    data_lines = lines[CSV_HEADER_ROWS:]
    if not data_lines:
        return None

    records = []
    for line in data_lines:
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            date_str = parts[0].strip()
            value_str = parts[2].strip()
            if not date_str or not value_str:
                continue
            date = datetime.strptime(date_str, "%Y-%m-%d")
            value = float(value_str)
            records.append({
                "day_of_year": date.timetuple().tm_yday,
                "value": value,
            })
        except (ValueError, IndexError):
            continue

    return records if records else None


def percentile(values: list[float], pct: float) -> float:
    """Calculate percentile using linear interpolation."""
    k = (pct / 100) * (len(values) - 1)
    f = int(k)
    c = f + 1
    if c >= len(values):
        return values[-1]
    return values[f] + (k - f) * (values[c] - values[f])


def compute_daily_percentiles(records: list[dict]) -> dict:
    """
    Compute percentiles for each day-of-year (1-366) using a rolling window.
    Returns dict keyed by day-of-year string.
    """
    # Group values by day-of-year
    by_day = defaultdict(list)
    for record in records:
        by_day[record["day_of_year"]].append(record["value"])

    daily_pcts = {}
    for target_day in range(1, 367):
        window_values = []
        for doy, values in by_day.items():
            diff = abs(doy - target_day)
            if diff > 182:
                diff = 365 - diff
            if diff <= PERCENTILE_WINDOW_DAYS:
                window_values.extend(values)

        if len(window_values) < 10:
            continue

        window_values.sort()
        daily_pcts[str(target_day)] = {
            "p10": round(percentile(window_values, 10), 4),
            "p25": round(percentile(window_values, 25), 4),
            "p50": round(percentile(window_values, 50), 4),
            "p75": round(percentile(window_values, 75), 4),
            "p90": round(percentile(window_values, 90), 4),
            "sample_size": len(window_values),
        }

    return daily_pcts


async def download_and_compute(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    station: dict,
) -> dict | None:
    """Download historical CSVs for a station and compute percentiles."""
    sn = station["station_number"]
    result = {"station_number": sn}
    has_data = False

    for data_key, keyword in [("flow", "flow"), ("level", "water level")]:
        url = find_dataset_url(station, keyword)
        if not url:
            continue

        async with semaphore:
            try:
                resp = await client.get(url, timeout=DOWNLOAD_TIMEOUT)
                resp.raise_for_status()
                text = resp.text
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                print(f"    {sn}: error downloading {data_key} CSV: {e}")
                continue

        records = parse_csv_content(text)
        if not records:
            continue

        daily_pcts = compute_daily_percentiles(records)
        if daily_pcts:
            result[data_key] = daily_pcts
            has_data = True

    return result if has_data else None


async def main():
    print("Loading stations...")
    stations = load_stations(STATIONS_FILE)

    # Filter to river and reservoir stations
    ratable = [s for s in stations if s.get("station_type") in ("R", "L")]
    print(f"Found {len(ratable)} river/reservoir stations to process")

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    all_percentiles = {}

    async with httpx.AsyncClient() as client:
        tasks = [
            download_and_compute(client, semaphore, station)
            for station in ratable
        ]

        total = len(tasks)
        completed = 0
        succeeded = 0

        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1

            if result:
                sn = result.pop("station_number")
                all_percentiles[sn] = result
                succeeded += 1
                keys = list(result.keys())
                print(f"  [{completed}/{total}] {sn}: {', '.join(keys)}")
            else:
                if completed % 50 == 0:
                    print(f"  [{completed}/{total}] processing...")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_percentiles, f, indent=2)

    print(f"\nDone. Percentiles computed for {succeeded}/{total} stations.")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
