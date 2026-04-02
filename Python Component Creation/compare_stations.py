"""
WaterPulse Station Comparison Script
=====================================
Compares stations from rivers.alberta.ca against ECCC's api.weather.gc.ca
to determine overlap, gaps, and migration priorities.

Usage:
    python compare_stations.py

Outputs:
    - Console summary with counts and breakdowns
    - compare_stations_report.json  (full structured data)
    - compare_stations_report.csv   (flat table for spreadsheet review)

Requirements:
    pip install httpx  (or: pip install httpx --break-system-packages)
"""

import asyncio
import csv
import json
import re
import sys
from datetime import datetime

try:
    import httpx
except ImportError:
    print("This script requires httpx. Install it with:")
    print("  pip install httpx --break-system-packages")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALBERTA_STATIONS_URL = (
    "https://rivers.alberta.ca/DataService/ListStationsAndAlerts"
)

ECCC_STATIONS_URL = (
    "https://api.weather.gc.ca/collections/hydrometric-stations/items"
)

ECCC_REALTIME_URL = (
    "https://api.weather.gc.ca/collections/hydrometric-realtime/items"
)

# ECCC paginates at 500 by default; max allowed per request
ECCC_PAGE_SIZE = 500

# Timeout for individual requests (seconds)
REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Alberta API
# ---------------------------------------------------------------------------

async def fetch_alberta_stations(client: httpx.AsyncClient) -> list[dict]:
    """
    Fetch all stations from rivers.alberta.ca.
    The response is double-encoded JSON (a JSON string inside a JSON string).
    """
    print("[Alberta] Fetching stations from rivers.alberta.ca ...")
    resp = await client.get(ALBERTA_STATIONS_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    # First decode — gives us a JSON string
    data = resp.json()

    # The payload may be double-encoded: a JSON string wrapping the real list.
    # Keep decoding while the result is still a string.
    while isinstance(data, str):
        data = json.loads(data)

    # data should now be a list of station dicts (or a dict containing one)
    if isinstance(data, dict):
        # Some Alberta responses wrap stations in a key
        for key in ("Stations", "stations", "data", "Data"):
            if key in data:
                data = data[key]
                break

    if not isinstance(data, list):
        print(f"[Alberta] WARNING: unexpected top-level type {type(data).__name__}")
        return []

    print(f"[Alberta] Received {len(data)} station records")
    return data


def normalise_alberta_station(raw: dict) -> dict:
    """
    Pull the fields we care about into a consistent shape.
    Alberta's API has varied key names across versions; try several.
    """
    def pick(keys, default=None):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return default

    station_number = pick([
        "StationNumber", "Station_Number", "station_number",
        "StationId", "Station_Id", "station_id",
        "Name", "StationName",  # fallback — will filter later
    ], "")

    # Clean up: some Alberta IDs have extra whitespace
    station_number = str(station_number).strip()

    return {
        "station_number": station_number,
        "station_name": pick([
            "StationName", "Station_Name", "station_name", "Name",
        ], ""),
        "station_type": pick([
            "StationType", "Station_Type", "station_type", "Type",
        ], ""),
        "basin": pick([
            "Basin", "BasinName", "basin", "basin_name",
        ], ""),
        "latitude": pick([
            "Latitude", "latitude", "Lat", "lat",
        ]),
        "longitude": pick([
            "Longitude", "longitude", "Lng", "lng", "Lon", "lon",
        ]),
        "_raw_keys": list(raw.keys()),
    }


# ---------------------------------------------------------------------------
# ECCC API
# ---------------------------------------------------------------------------

async def fetch_eccc_alberta_stations(client: httpx.AsyncClient) -> list[dict]:
    """
    Fetch all ECCC hydrometric stations in Alberta (active + discontinued),
    paginating through the OGC API.
    """
    print("[ECCC] Fetching Alberta stations from api.weather.gc.ca ...")
    all_features = []
    offset = 0

    while True:
        params = {
            "PROV_TERR_STATE_LOC": "AB",
            "f": "json",
            "limit": ECCC_PAGE_SIZE,
            "offset": offset,
        }
        resp = await client.get(
            ECCC_STATIONS_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        all_features.extend(features)
        print(f"  ... fetched {len(all_features)} so far (offset={offset})")

        if len(features) < ECCC_PAGE_SIZE:
            break  # last page
        offset += ECCC_PAGE_SIZE

    print(f"[ECCC] Total Alberta station records: {len(all_features)}")
    return all_features


async def fetch_eccc_realtime_station_ids(client: httpx.AsyncClient) -> set[str]:
    """
    Fetch a sample of real-time readings for Alberta to discover which
    stations are actively reporting right now.
    We ask for the last day of data sorted newest-first, then deduplicate.
    """
    print("[ECCC] Fetching real-time station list for Alberta ...")
    station_ids = set()
    offset = 0

    while True:
        params = {
            "PROV_TERR_STATE_LOC": "AB",
            "f": "json",
            "limit": ECCC_PAGE_SIZE,
            "offset": offset,
            "sortby": "-DATETIME",
            "properties": "STATION_NUMBER",  # only need this field
        }
        resp = await client.get(
            ECCC_REALTIME_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        for f in features:
            stn = f.get("properties", {}).get("STATION_NUMBER")
            if stn:
                station_ids.add(stn)

        if len(features) < ECCC_PAGE_SIZE:
            break
        offset += ECCC_PAGE_SIZE

        # Safety: real-time can have millions of rows; once we've seen enough
        # unique stations, we can stop.  After ~5,000 rows we likely have
        # every station represented at least once.
        if offset > 10000:
            break

    print(f"[ECCC] Real-time active stations in AB: {len(station_ids)}")
    return station_ids


def normalise_eccc_station(feature: dict) -> dict:
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [None, None])
    return {
        "station_number": props.get("STATION_NUMBER", ""),
        "station_name": props.get("STATION_NAME", ""),
        "status": props.get("STATUS_EN", ""),
        "real_time": bool(props.get("REAL_TIME", 0)),
        "drainage_area_gross": props.get("DRAINAGE_AREA_GROSS"),
        "contributor": props.get("CONTRIBUTOR_EN", ""),
        "latitude": coords[1] if len(coords) > 1 else None,
        "longitude": coords[0] if len(coords) > 0 else None,
    }


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

# WSC station numbers follow pattern: 2 digits + 2 letters + 3 digits
# e.g. 05AA004, 07BE001
WSC_PATTERN = re.compile(r"^\d{2}[A-Z]{2}\d{3}$")


def is_wsc_id(station_number: str) -> bool:
    return bool(WSC_PATTERN.match(station_number.strip().upper()))


def classify_station_type(type_code: str) -> str:
    """Map Alberta's type codes to human-readable labels."""
    code = str(type_code).strip().upper()
    return {
        "R": "River",
        "L": "Lake/Reservoir",
        "M": "Meteorological",
    }.get(code, f"Unknown ({type_code})")


# ---------------------------------------------------------------------------
# Analysis and reporting
# ---------------------------------------------------------------------------

def analyse(
    ab_stations: list[dict],
    eccc_stations: list[dict],
    eccc_realtime_ids: set[str],
) -> dict:
    """Build the comparison report."""

    # Index ECCC stations by station_number
    eccc_by_id = {s["station_number"]: s for s in eccc_stations}
    eccc_ids = set(eccc_by_id.keys())

    # Index Alberta stations by station_number
    ab_by_id = {}
    for s in ab_stations:
        sid = s["station_number"]
        if sid:
            ab_by_id[sid] = s
    ab_ids = set(ab_by_id.keys())

    # --- Set operations ---
    in_both = ab_ids & eccc_ids
    ab_only = ab_ids - eccc_ids
    eccc_only = eccc_ids - ab_ids

    # --- Sub-classify Alberta-only stations ---
    ab_only_wsc = {s for s in ab_only if is_wsc_id(s)}
    ab_only_non_wsc = ab_only - ab_only_wsc

    ab_only_by_type = {}
    for sid in ab_only:
        st = classify_station_type(ab_by_id[sid].get("station_type", ""))
        ab_only_by_type.setdefault(st, []).append(sid)

    # --- Alberta station type breakdown (all) ---
    ab_type_counts = {}
    for s in ab_stations:
        st = classify_station_type(s.get("station_type", ""))
        ab_type_counts[st] = ab_type_counts.get(st, 0) + 1

    # --- ECCC status breakdown ---
    eccc_active = [s for s in eccc_stations if s["status"] == "Active"]
    eccc_discontinued = [s for s in eccc_stations if s["status"] == "Discontinued"]
    eccc_realtime_flagged = [s for s in eccc_stations if s["real_time"]]

    # --- Overlap detail: which shared stations have live ECCC data? ---
    overlap_with_realtime = in_both & eccc_realtime_ids

    # --- Build per-station detail rows ---
    all_station_ids = sorted(ab_ids | eccc_ids)
    detail_rows = []
    for sid in all_station_ids:
        ab_s = ab_by_id.get(sid, {})
        eccc_s = eccc_by_id.get(sid, {})
        detail_rows.append({
            "station_number": sid,
            "station_name": ab_s.get("station_name") or eccc_s.get("station_name", ""),
            "in_alberta_api": sid in ab_ids,
            "in_eccc_api": sid in eccc_ids,
            "alberta_type": ab_s.get("station_type", ""),
            "eccc_status": eccc_s.get("status", ""),
            "eccc_realtime_flag": eccc_s.get("real_time", False),
            "eccc_has_recent_data": sid in eccc_realtime_ids,
            "is_wsc_id": is_wsc_id(sid),
            "basin": ab_s.get("basin", ""),
            "latitude": ab_s.get("latitude") or eccc_s.get("latitude"),
            "longitude": ab_s.get("longitude") or eccc_s.get("longitude"),
        })

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "alberta_total": len(ab_ids),
            "eccc_total_alberta": len(eccc_ids),
            "eccc_active": len(eccc_active),
            "eccc_discontinued": len(eccc_discontinued),
            "eccc_realtime_flagged": len(eccc_realtime_flagged),
            "eccc_actually_reporting": len(eccc_realtime_ids),
            "in_both_apis": len(in_both),
            "alberta_only": len(ab_only),
            "eccc_only": len(eccc_only),
            "overlap_with_live_eccc_data": len(overlap_with_realtime),
        },
        "alberta_type_breakdown": ab_type_counts,
        "alberta_only_stations": {
            "total": len(ab_only),
            "wsc_format_ids": sorted(ab_only_wsc),
            "non_wsc_format_ids": sorted(ab_only_non_wsc),
            "by_type": {k: sorted(v) for k, v in ab_only_by_type.items()},
        },
        "eccc_only_stations": {
            "total": len(eccc_only),
            "sample": sorted(eccc_only)[:30],
        },
        "detail": detail_rows,
    }

    return report


def print_report(report: dict):
    """Pretty-print the key findings to the console."""
    s = report["summary"]
    ab_types = report["alberta_type_breakdown"]
    ab_only = report["alberta_only_stations"]

    print("\n" + "=" * 68)
    print("  WATERPULSE STATION COMPARISON REPORT")
    print("=" * 68)

    print(f"\n  Generated: {report['generated_at']}\n")

    print("  STATION COUNTS")
    print("  " + "-" * 40)
    print(f"  Alberta API (rivers.alberta.ca):  {s['alberta_total']:>6}")
    print(f"  ECCC API (Alberta only):          {s['eccc_total_alberta']:>6}")
    print(f"    ├─ Active:                      {s['eccc_active']:>6}")
    print(f"    ├─ Discontinued:                {s['eccc_discontinued']:>6}")
    print(f"    ├─ Real-time flag set:          {s['eccc_realtime_flagged']:>6}")
    print(f"    └─ Actually reporting now:       {s['eccc_actually_reporting']:>6}")

    print(f"\n  OVERLAP ANALYSIS")
    print("  " + "-" * 40)
    print(f"  In BOTH APIs:                     {s['in_both_apis']:>6}")
    print(f"    └─ With live ECCC data:         {s['overlap_with_live_eccc_data']:>6}")
    print(f"  Alberta-only stations:            {s['alberta_only']:>6}")
    print(f"  ECCC-only stations (AB):          {s['eccc_only']:>6}")

    overlap_pct = (
        (s["in_both_apis"] / s["alberta_total"] * 100)
        if s["alberta_total"] > 0
        else 0
    )
    print(f"\n  Coverage: {overlap_pct:.1f}% of Alberta stations are also in ECCC")

    print(f"\n  ALBERTA STATION TYPE BREAKDOWN (all {s['alberta_total']})")
    print("  " + "-" * 40)
    for type_name, count in sorted(ab_types.items()):
        print(f"  {type_name:<30} {count:>6}")

    print(f"\n  ALBERTA-ONLY STATIONS ({ab_only['total']} total)")
    print("  " + "-" * 40)
    print(f"  With WSC-format IDs:              {len(ab_only['wsc_format_ids']):>6}")
    print(f"  With non-WSC IDs:                 {len(ab_only['non_wsc_format_ids']):>6}")

    if ab_only["by_type"]:
        print(f"\n  Alberta-only by type:")
        for type_name, stations in sorted(ab_only["by_type"].items()):
            print(f"    {type_name:<28} {len(stations):>4}")

    if ab_only["non_wsc_format_ids"]:
        print(f"\n  Non-WSC station IDs (provincial-only):")
        for sid in ab_only["non_wsc_format_ids"][:20]:
            name = ""
            for row in report["detail"]:
                if row["station_number"] == sid:
                    name = row["station_name"]
                    break
            print(f"    {sid:<20} {name}")
        if len(ab_only["non_wsc_format_ids"]) > 20:
            print(f"    ... and {len(ab_only['non_wsc_format_ids']) - 20} more")

    if ab_only["wsc_format_ids"]:
        print(f"\n  WSC-format IDs only in Alberta API (possible ECCC gaps):")
        for sid in ab_only["wsc_format_ids"][:20]:
            name = ""
            for row in report["detail"]:
                if row["station_number"] == sid:
                    name = row["station_name"]
                    break
            print(f"    {sid:<12} {name}")
        if len(ab_only["wsc_format_ids"]) > 20:
            print(f"    ... and {len(ab_only['wsc_format_ids']) - 20} more")

    print(f"\n  ECCC-ONLY STATIONS ({report['eccc_only_stations']['total']})")
    print("  " + "-" * 40)
    print("  These are in ECCC but NOT in rivers.alberta.ca.")
    print("  Expanding to ECCC gains these stations for free.")
    sample = report["eccc_only_stations"]["sample"]
    for sid in sample[:15]:
        for row in report["detail"]:
            if row["station_number"] == sid:
                status = row["eccc_status"]
                print(f"    {sid:<12} [{status}]")
                break
    if len(sample) > 15:
        print(f"    ... and {report['eccc_only_stations']['total'] - 15} more")

    # --- Priority recommendation ---
    print(f"\n  MIGRATION PRIORITY RECOMMENDATION")
    print("  " + "-" * 40)
    if overlap_pct > 90:
        print("  HIGH OVERLAP — ECCC covers the vast majority of Alberta")
        print("  stations.  Safe to migrate to ECCC as primary source.")
    elif overlap_pct > 70:
        print("  GOOD OVERLAP — Most stations are covered.  Keep Alberta")
        print("  API as supplementary source for the gaps.")
    else:
        print("  PARTIAL OVERLAP — Significant gaps exist.  Consider a")
        print("  dual-source approach for the Alberta market.")

    met_only = len(ab_only["by_type"].get("Meteorological", []))
    non_met_gap = ab_only["total"] - met_only
    if met_only > 0:
        print(f"\n  Of the {ab_only['total']} Alberta-only stations:")
        print(f"    {met_only} are Meteorological (type M) — ECCC has this data")
        print(f"      in separate collections (swob-realtime, climate-hourly)")
        print(f"    {non_met_gap} are River/Lake — these are the real gap to assess")

    print("\n" + "=" * 68)


def save_csv(report: dict, filepath: str):
    """Write the detail rows to a CSV for spreadsheet review."""
    rows = report["detail"]
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n  CSV saved to: {filepath}")


def save_json(report: dict, filepath: str):
    """Write the full report to JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  JSON saved to: {filepath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("WaterPulse Station Comparison")
    print("Comparing rivers.alberta.ca vs api.weather.gc.ca (Alberta)\n")

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"Accept": "application/json"},
    ) as client:

        # --- Fetch from both sources concurrently ---
        ab_raw_task = fetch_alberta_stations(client)
        eccc_raw_task = fetch_eccc_alberta_stations(client)
        eccc_rt_task = fetch_eccc_realtime_station_ids(client)

        ab_raw, eccc_raw, eccc_rt_ids = await asyncio.gather(
            ab_raw_task, eccc_raw_task, eccc_rt_task
        )

    # --- Debug: show a sample of raw Alberta keys so we parse correctly ---
    if ab_raw:
        sample = ab_raw[0]
        print(f"\n[Debug] Sample Alberta station keys: {list(sample.keys())[:15]}")
        # Show first station for manual inspection
        print(f"[Debug] First Alberta station: {json.dumps(sample, indent=2, default=str)[:500]}")

    # --- Normalise ---
    ab_stations = [normalise_alberta_station(s) for s in ab_raw]
    eccc_stations = [normalise_eccc_station(f) for f in eccc_raw]

    # Filter out Alberta records that didn't parse a station number
    ab_stations = [s for s in ab_stations if s["station_number"]]

    # --- Analyse ---
    report = analyse(ab_stations, eccc_stations, eccc_rt_ids)

    # --- Output ---
    print_report(report)
    save_json(report, "compare_stations_report.json")
    save_csv(report, "compare_stations_report.csv")

    print("\nDone! Review the CSV in a spreadsheet for full station-by-station detail.\n")


if __name__ == "__main__":
    asyncio.run(main())
