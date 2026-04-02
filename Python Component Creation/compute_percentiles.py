"""
compute_percentiles.py

Background job that downloads 365-day historical CSVs from rivers.alberta.ca,
computes daily mean values for flow and level, and accumulates them in
historical_data.json (up to 5 years per station per date).

If historical_data.json already exists, new daily means are appended.
Duplicate years are overwritten with the latest data.
Data older than 5 years is pruned.

Run this yearly (or more often to keep data fresh):
    python compute_percentiles.py
"""

import asyncio
import json
from datetime import datetime
from collections import defaultdict

import httpx

STATIONS_FILE = "stations_extracted.json"
HISTORICAL_FILE = "historical_data.json"

# Number of header/disclaimer rows to skip in historical CSVs
CSV_HEADER_ROWS = 22

# Maximum years of historical data to retain per station per date
MAX_YEARS = 5

# Max concurrent CSV downloads
MAX_CONCURRENCY = 10

# Timeout for CSV downloads (some files are 3MB+)
DOWNLOAD_TIMEOUT = 60


def load_stations(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def load_existing_historical(path: str) -> dict:
    """Load existing historical data or return empty dict."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  No existing {path} found. Starting fresh.\n")
        return {}


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


def parse_csv_to_daily_means(text: str) -> dict:
    """
    Parse a historical CSV into daily mean values.
    Returns dict keyed by (year, month_day) -> mean value.
    Example: {(2025, "03-19"): 42.3, (2025, "03-20"): 41.8, ...}
    """
    lines = text.splitlines()
    data_lines = lines[CSV_HEADER_ROWS:]
    if not data_lines:
        return {}

    # Accumulate readings per date
    daily_readings = defaultdict(list)

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
            year = date.year
            month_day = date.strftime("%m-%d")
            daily_readings[(year, month_day)].append(value)
        except (ValueError, IndexError):
            continue

    # Compute mean for each date
    daily_means = {}
    for (year, month_day), values in daily_readings.items():
        daily_means[(year, month_day)] = round(sum(values) / len(values), 4)

    return daily_means


def merge_daily_means(
    existing_station: dict,
    data_key: str,
    new_daily_means: dict,
) -> dict:
    """
    Merge new daily means into existing station data.
    Overwrites duplicate years, prunes to MAX_YEARS.
    """
    if data_key not in existing_station:
        existing_station[data_key] = {}

    date_data = existing_station[data_key]

    # Add new means
    for (year, month_day), mean_value in new_daily_means.items():
        if month_day not in date_data:
            date_data[month_day] = []

        entries = date_data[month_day]

        # Remove existing entry for same year (overwrite)
        entries = [e for e in entries if e["year"] != year]

        # Add new entry
        entries.append({"year": year, "value": mean_value})

        # Sort by year descending, keep only the most recent MAX_YEARS
        entries.sort(key=lambda e: e["year"], reverse=True)
        date_data[month_day] = entries[:MAX_YEARS]

    existing_station[data_key] = date_data
    return existing_station


async def download_and_process(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    station: dict,
    existing_historical: dict,
) -> tuple[str, dict] | None:
    """Download historical CSVs for a station and compute daily means."""
    sn = station["station_number"]
    station_data = existing_historical.get(sn, {})
    has_new_data = False

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

        daily_means = parse_csv_to_daily_means(text)
        if not daily_means:
            continue

        station_data = merge_daily_means(station_data, data_key, daily_means)
        has_new_data = True

    if has_new_data:
        return (sn, station_data)
    elif sn in existing_historical:
        # Keep existing data even if download failed
        return (sn, existing_historical[sn])
    return None


async def main():
    print("Loading stations...")
    stations = load_stations(STATIONS_FILE)

    # Filter to river and reservoir stations
    ratable = [s for s in stations if s.get("station_type") in ("R", "L")]
    print(f"Found {len(ratable)} river/reservoir stations to process")

    print("Loading existing historical data...")
    existing_historical = load_existing_historical(HISTORICAL_FILE)
    existing_count = len(existing_historical)
    print(f"Loaded existing data for {existing_count} stations\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    updated_historical = {}

    # Preserve stations in existing data that aren't being re-processed
    for sn, data in existing_historical.items():
        updated_historical[sn] = data

    async with httpx.AsyncClient() as client:
        tasks = [
            download_and_process(client, semaphore, station, existing_historical)
            for station in ratable
        ]

        total = len(tasks)
        completed = 0
        succeeded = 0

        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1

            if result:
                sn, station_data = result
                updated_historical[sn] = station_data
                succeeded += 1

                # Show years of data for this station
                sample_key = next(iter(station_data), None)
                if sample_key:
                    sample_date = next(iter(station_data[sample_key]), None)
                    if sample_date:
                        years = [
                            e["year"]
                            for e in station_data[sample_key][sample_date]
                        ]
                        print(
                            f"  [{completed}/{total}] {sn}: "
                            f"{', '.join(station_data.keys())} "
                            f"(years: {years})"
                        )
                    else:
                        print(f"  [{completed}/{total}] {sn}: updated")
                else:
                    print(f"  [{completed}/{total}] {sn}: updated")
            else:
                if completed % 50 == 0 or completed == total:
                    print(f"  [{completed}/{total}] processing...")

    with open(HISTORICAL_FILE, "w") as f:
        json.dump(updated_historical, f)

    # Summary
    total_stations = len(updated_historical)
    sample_sn = next(iter(updated_historical), None)
    if sample_sn:
        sample = updated_historical[sample_sn]
        sample_key = next(iter(sample), None)
        if sample_key:
            sample_date = next(iter(sample[sample_key]), None)
            if sample_date:
                sample_years = len(sample[sample_key][sample_date])
                print(f"\nSample: {sample_sn} has {sample_years} year(s) of data")

    print(f"\nDone. Historical data saved for {total_stations} stations.")
    print(f"  New/updated: {succeeded}")
    print(f"  Preserved from previous runs: {total_stations - succeeded}")
    print(f"Saved to {HISTORICAL_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
