import json
import requests

FIELDS_TO_KEEP = [
    # Core identification
    "station_number",
    "station_name",
    "station_latitude",
    "station_longitude",
    "basin_number",
    "station_type",
    "data_type",
    "WMOReports",
    # Rating scale (TSIDs for 25th/75th percentile series)
    "PCT25",
    "PCT75",
    # Reservoir features
    "hasCapacity",
    "liveStorage",
    "pctFull",
    # Context for users
    "parameter_data_status",
    "ptValueLast6h",
    "ptValueLast12h",
    "ptValueLast24h",
    "ptValueLast48h",
    "SECRIVER",
    # Data sourcing
    "TSID",
    "catchment_number",
    # Historical data CSV/JSON links
    "datasets",
]

SOURCE_URL = "https://rivers.alberta.ca/DataService/ListStationsAndAlerts"


def extract_stations(output_path: str) -> None:
    response = requests.get(SOURCE_URL)
    response.raise_for_status()
    json_file = response.json()

    # Un-"nests" the JSON response
    entries = json.loads(json_file["stations"])["WISKI_ABRivers_station_parameters"]

    print(f"Found {len(entries)} station entries")

    extracted = []
    for entry in entries:
        station = {field: entry.get(field) for field in FIELDS_TO_KEEP}
        extracted.append(station)

    with open(output_path, "w") as f:
        json.dump(extracted, f, indent=2)

    print(f"Extracted {len(extracted)} stations to {output_path}")


if __name__ == "__main__":
    extract_stations(output_path="stations_extracted.json")