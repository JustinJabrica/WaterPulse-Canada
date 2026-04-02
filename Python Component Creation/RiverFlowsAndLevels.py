"""
RiverFlowsAndLevels.py

Fetches current river/reservoir readings from rivers.alberta.ca and rates
them against historical percentiles computed from accumulated daily means.

Prerequisites:
    1. Run ListStationsAndAlertsFromURL.py to generate stations_extracted.json
    2. Run compute_percentiles.py to generate historical_data.json

Usage:
    python RiverFlowsAndLevels.py
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx

STATIONS_FILE = "stations_extracted.json"
HISTORICAL_FILE = "historical_data.json"
OUTPUT_FILE = "river_levels_and_flows.json"
WATERLEVEL_RECORDS_URL = "https://rivers.alberta.ca/DataService/WaterlevelRecords"

# Days on either side of the target date for the percentile window
PERCENTILE_WINDOW_DAYS = 7

# Max concurrent requests to rivers.alberta.ca
MAX_CONCURRENCY = 15

# Request timeout in seconds
REQUEST_TIMEOUT = 15


# ──────────────────────────────────────────────────────────────────────
# Station loading and selection
# ──────────────────────────────────────────────────────────────────────


def load_stations(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def load_historical(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  Warning: {path} not found. Run compute_percentiles.py first.")
        print(f"  Ratings will not be available.\n")
        return {}


def build_prefix_groups(stations: list) -> dict:
    groups = defaultdict(list)
    for station in stations:
        sn = station.get("station_number", "")
        if len(sn) >= 4:
            groups[sn[:4]].append(station)
    return dict(groups)


def build_basin_groups(prefix_groups: dict) -> dict:
    basins = defaultdict(list)
    for prefix, stations in prefix_groups.items():
        basin = stations[0].get("basin_number", "Unknown")
        basins[basin].append(prefix)
    return dict(basins)


def display_basins(basin_groups: dict, prefix_groups: dict) -> None:
    print("\n===== AVAILABLE BASINS =====\n")
    for i, (basin, prefixes) in enumerate(sorted(basin_groups.items()), 1):
        total = sum(len(prefix_groups[p]) for p in prefixes)
        print(f"  {i:>3}. {basin} ({total} stations, {len(prefixes)} groups)")
    print()


def display_prefixes(prefix_groups: dict, prefixes_to_show: list) -> None:
    print("\n===== STATION GROUPS =====\n")
    for i, prefix in enumerate(sorted(prefixes_to_show), 1):
        stations = prefix_groups[prefix]
        basin = stations[0].get("basin_number", "Unknown")
        sample_names = [s["station_name"] for s in stations[:3]]
        preview = ", ".join(sample_names)
        if len(stations) > 3:
            preview += f", ... (+{len(stations) - 3} more)"
        print(f"  {i:>3}. [{prefix}] Basin: {basin} ({len(stations)} stations)")
        print(f"       {preview}")
    print()


def select_stations(stations: list) -> None | list | list[Any]:
    prefix_groups = build_prefix_groups(stations)
    basin_groups = build_basin_groups(prefix_groups)

    while True:
        print("\n===== STATION SELECTION =====")
        print("  1. Browse by basin")
        print("  2. Browse all station groups")
        print("  3. Enter station group code(s) directly")
        print("  4. Fetch all stations (warning: ~961 requests)")
        print("  0. Exit")

        choice = input("\nSelect an option: ").strip()

        if choice == "0":
            return []

        if choice == "1":
            display_basins(basin_groups, prefix_groups)
            basin_input = input(
                "Enter basin number (e.g., 1) or basin name (e.g., BOW): "
            ).strip()
            sorted_basins = sorted(basin_groups.keys())
            selected_basin = None
            if basin_input.isdigit():
                idx = int(basin_input) - 1
                if 0 <= idx < len(sorted_basins):
                    selected_basin = sorted_basins[idx]
            else:
                basin_upper = basin_input.upper()
                if basin_upper in basin_groups:
                    selected_basin = basin_upper
            if not selected_basin:
                print("Invalid selection.")
                continue

            prefixes = basin_groups[selected_basin]
            display_prefixes(prefix_groups, prefixes)
            prefix_input = input(
                "Enter group number(s) separated by commas (or 'all' for entire basin): "
            ).strip()
            if prefix_input.lower() == "all":
                selected_prefixes = prefixes
            else:
                sorted_prefixes = sorted(prefixes)
                selected_prefixes = []
                for num in prefix_input.split(","):
                    num = num.strip()
                    if num.isdigit():
                        idx = int(num) - 1
                        if 0 <= idx < len(sorted_prefixes):
                            selected_prefixes.append(sorted_prefixes[idx])
            if not selected_prefixes:
                print("No valid groups selected.")
                continue
            selected = []
            for p in selected_prefixes:
                selected.extend(prefix_groups[p])
            return selected

        elif choice == "2":
            all_prefixes = list(prefix_groups.keys())
            display_prefixes(prefix_groups, all_prefixes)
            prefix_input = input(
                "Enter group number(s) separated by commas: "
            ).strip()
            sorted_prefixes = sorted(all_prefixes)
            selected_prefixes = []
            for num in prefix_input.split(","):
                num = num.strip()
                if num.isdigit():
                    idx = int(num) - 1
                    if 0 <= idx < len(sorted_prefixes):
                        selected_prefixes.append(sorted_prefixes[idx])
            if not selected_prefixes:
                print("No valid groups selected.")
                continue
            selected = []
            for p in selected_prefixes:
                selected.extend(prefix_groups[p])
            return selected

        elif choice == "3":
            codes_input = input(
                "Enter 4-character group code(s) separated by commas (e.g., 05BH,05BJ): "
            ).strip()
            selected = []
            for code in codes_input.split(","):
                code = code.strip()
                if code in prefix_groups:
                    selected.extend(prefix_groups[code])
                else:
                    print(f"  Warning: '{code}' not found, skipping.")
            if selected:
                return selected
            print("No valid codes entered.")
            continue

        elif choice == "4":
            confirm = input(
                f"This will make {len(stations)} requests. Continue? (y/n): "
            ).strip()
            if confirm.lower() == "y":
                return stations
            continue
        else:
            print("Invalid option.")


# ──────────────────────────────────────────────────────────────────────
# Percentile calculation from accumulated historical daily means
# ──────────────────────────────────────────────────────────────────────


def get_window_dates(target_date: datetime) -> list[str]:
    """
    Generate MM-DD strings for a ±PERCENTILE_WINDOW_DAYS window
    around the target date, handling month/year boundaries correctly.
    """
    dates = []
    for offset in range(-PERCENTILE_WINDOW_DAYS, PERCENTILE_WINDOW_DAYS + 1):
        d = target_date + timedelta(days=offset)
        dates.append(d.strftime("%m-%d"))
    return dates


def compute_percentiles(values: list[float]) -> dict | None:
    """Compute percentiles from a list of values. Returns None if too few."""
    if len(values) < 5:
        return None

    values.sort()

    def pct(vals, p):
        k = (p / 100) * (len(vals) - 1)
        f = int(k)
        c = f + 1
        if c >= len(vals):
            return vals[-1]
        return vals[f] + (k - f) * (vals[c] - vals[f])

    return {
        "p10": round(pct(values, 10), 4),
        "p25": round(pct(values, 25), 4),
        "p50": round(pct(values, 50), 4),
        "p75": round(pct(values, 75), 4),
        "p90": round(pct(values, 90), 4),
        "sample_size": len(values),
    }


def get_station_percentiles(
    station_number: str,
    data_key: str,
    historical_db: dict,
    target_date: datetime,
) -> dict | None:
    """
    Collect daily mean values within the window across all stored years
    and compute percentiles.
    """
    station_data = historical_db.get(station_number, {})
    date_data = station_data.get(data_key, {})

    if not date_data:
        return None

    window_dates = get_window_dates(target_date)

    # Pool all values from all years within the window
    values = []
    for md in window_dates:
        entries = date_data.get(md, [])
        for entry in entries:
            values.append(entry["value"])

    return compute_percentiles(values)


# ──────────────────────────────────────────────────────────────────────
# Rating logic
# ──────────────────────────────────────────────────────────────────────


def rate_value(value: float | None, percentiles: dict | None) -> str | None:
    """Rate a value against percentile thresholds."""
    if value is None or percentiles is None:
        return None
    if value < percentiles["p10"]:
        return "very low"
    elif value < percentiles["p25"]:
        return "low"
    elif value <= percentiles["p75"]:
        return "average"
    elif value <= percentiles["p90"]:
        return "high"
    else:
        return "very high"


def apply_ratings(
    current: dict,
    station: dict,
    historical_db: dict,
    target_date: datetime,
) -> None:
    """Compute percentiles from historical data and apply ratings."""
    sn = station["station_number"]

    # Rate flow or outflow
    flow_value = current.get("flow") or current.get("outflow")
    flow_pcts = get_station_percentiles(sn, "flow", historical_db, target_date)
    current["flow_rating"] = rate_value(flow_value, flow_pcts)
    current["flow_percentiles"] = flow_pcts

    # Rate water level
    level_value = current.get("level")
    level_pcts = get_station_percentiles(sn, "level", historical_db, target_date)
    current["level_rating"] = rate_value(level_value, level_pcts)
    current["level_percentiles"] = level_pcts

    # Rate reservoir fullness (fixed scale)
    current["pct_full_rating"] = None
    if station.get("hasCapacity") and current.get("pct_full") is not None:
        pct_full = current["pct_full"]
        if pct_full < 20:
            current["pct_full_rating"] = "very low"
        elif pct_full < 40:
            current["pct_full_rating"] = "low"
        elif pct_full <= 70:
            current["pct_full_rating"] = "average"
        elif pct_full <= 90:
            current["pct_full_rating"] = "high"
        else:
            current["pct_full_rating"] = "very high"


# ──────────────────────────────────────────────────────────────────────
# Async current data fetching
# ──────────────────────────────────────────────────────────────────────


def parse_station_response(raw_json: str | list, station: dict) -> dict | None:
    """Parse the Water level - Records response into a structured dict."""
    if isinstance(raw_json, str):
        raw_json = json.loads(raw_json)

    if not raw_json or not isinstance(raw_json, list) or len(raw_json) == 0:
        return None

    entry = raw_json[0]
    data_rows = entry.get("data", [])
    if not data_rows:
        return None

    # Find the last row with non-null values
    newest = None
    for row in reversed(data_rows):
        if len(row) > 1 and row[1] is not None:
            newest = row
            break
    if not newest:
        return None

    columns = entry.get("columnarray", [])
    units = entry.get("ts_unitsymbols", [])

    result = {
        "station_number": station["station_number"],
        "station_name": station["station_name"],
        "station_latitude": station["station_latitude"],
        "station_longitude": station["station_longitude"],
        "basin_number": station["basin_number"],
        "station_type": station["station_type"],
        "data_type": station["data_type"],
        "has_capacity": station.get("hasCapacity", False),
        "timestamp": newest[0] if len(newest) > 0 else None,
    }

    for i, col_name in enumerate(columns):
        if i == 0:
            continue
        key = col_name.lower().replace(" ", "_").replace("%", "pct")
        result[key] = newest[i] if i < len(newest) else None
        unit_key = f"{key}_unit"
        result[unit_key] = units[i - 1] if (i - 1) < len(units) else None

    return result


async def fetch_station(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    station: dict,
    historical_db: dict,
    target_date: datetime,
) -> dict | None:
    """Fetch current data for a single station and apply ratings."""
    async with semaphore:
        try:
            response = await client.post(
                WATERLEVEL_RECORDS_URL,
                data={
                    "stationNumber": station["station_number"],
                    "stationType": station["station_type"],
                    "dataType": station["data_type"],
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            raw = response.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

    current = parse_station_response(raw, station)
    if not current:
        return None

    apply_ratings(current, station, historical_db, target_date)
    return current


async def fetch_all_stations(
    stations: list,
    historical_db: dict,
    target_date: datetime,
) -> list[dict]:
    """Fetch current data for all stations concurrently."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results = []

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_station(client, semaphore, station, historical_db, target_date)
            for station in stations
        ]

        total = len(tasks)
        completed = 0

        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1

            if result:
                results.append(result)
                flow_r = result.get("flow_rating") or "N/A"
                level_r = result.get("level_rating") or "N/A"
                print(
                    f"  [{completed}/{total}] {result['station_name']}"
                    f" — Flow: {flow_r.upper()}, Level: {level_r.upper()}"
                )
            else:
                if completed % 25 == 0 or completed == total:
                    print(f"  [{completed}/{total}] processing...")

    return results


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


def main():
    print("Loading stations...")
    stations = load_stations(STATIONS_FILE)
    print(f"Loaded {len(stations)} stations")

    print("Loading historical data...")
    historical_db = load_historical(HISTORICAL_FILE)
    hist_count = len(historical_db)

    # Show years of data for a sample station
    if historical_db:
        sample_sn = next(iter(historical_db))
        sample = historical_db[sample_sn]
        sample_key = next(iter(sample), None)
        if sample_key:
            sample_date = next(iter(sample[sample_key]), None)
            if sample_date:
                years = [e["year"] for e in sample[sample_key][sample_date]]
                print(
                    f"Loaded historical data for {hist_count} stations "
                    f"(sample: {sample_sn} has {len(years)} year(s): {years})"
                )
            else:
                print(f"Loaded historical data for {hist_count} stations")
        else:
            print(f"Loaded historical data for {hist_count} stations")
    else:
        print("No historical data available")

    selected = select_stations(stations)
    if not selected:
        print("No stations selected. Exiting.")
        return

    ratable = [s for s in selected if s["station_type"] in ("R", "L")]
    skipped = len(selected) - len(ratable)
    if skipped > 0:
        print(
            f"\nNote: Skipping {skipped} meteorological stations (M type)"
            f" — rating not applicable."
        )

    if not ratable:
        print("No river or reservoir stations in selection. Exiting.")
        return

    target_date = datetime.now()
    print(
        f"\nFetching current data for {len(ratable)} stations "
        f"(rating against {target_date.strftime('%m-%d')} "
        f"±{PERCENTILE_WINDOW_DAYS} days)...\n"
    )

    start_time = datetime.now()
    results = asyncio.run(fetch_all_stations(ratable, historical_db, target_date))
    elapsed = (datetime.now() - start_time).total_seconds()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {len(results)} stations fetched and rated in {elapsed:.1f}s\n")
    for r in sorted(results, key=lambda x: x["station_number"]):
        name = r["station_name"]
        flow_r = r.get("flow_rating") or "N/A"
        level_r = r.get("level_rating") or "N/A"
        pct_r = r.get("pct_full_rating")
        line = f"  {name}"
        line += f"\n    Flow: {flow_r.upper()}  |  Level: {level_r.upper()}"
        if pct_r:
            line += f"  |  Reservoir: {pct_r.upper()}"
        print(line)

    print(f"\nResults saved to {OUTPUT_FILE}")
    print(
        f"Total time: {elapsed:.1f}s "
        f"({len(results) / max(elapsed, 0.1):.1f} stations/sec)"
    )


if __name__ == "__main__":
    main()
