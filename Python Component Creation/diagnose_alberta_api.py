"""
Alberta API Diagnostic
======================
Dumps the raw response from rivers.alberta.ca so we can see
the exact key names and structure.

Usage:
    python diagnose_alberta_api.py

Outputs:
    alberta_raw_sample.json  — first 3 stations, pretty-printed
    Console output showing structure at every decoding step
"""

import json
import sys

try:
    import httpx
except ImportError:
    print("pip install httpx --break-system-packages")
    sys.exit(1)


URL = "https://rivers.alberta.ca/DataService/ListStationsAndAlerts"


def main():
    print("Fetching from rivers.alberta.ca ...\n")

    client = httpx.Client(follow_redirects=True, timeout=60)
    resp = client.get(URL)
    print(f"HTTP status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type', '?')}")
    print(f"Response length: {len(resp.text)} chars")
    print()

    # --- Step 1: Raw text preview ---
    raw_text = resp.text
    print("=== RAW RESPONSE (first 500 chars) ===")
    print(raw_text[:500])
    print("...\n")

    # --- Step 2: Decode layers ---
    data = raw_text
    decode_step = 0

    while isinstance(data, str):
        decode_step += 1
        try:
            data = json.loads(data)
            type_name = type(data).__name__
            print(f"Decode step {decode_step}: got {type_name}")

            if isinstance(data, dict):
                print(f"  Top-level keys: {list(data.keys())}")
                # Check each key for a list of stations
                for key in data:
                    val = data[key]
                    if isinstance(val, list) and len(val) > 0:
                        print(f"  Key '{key}' → list of {len(val)} items")
                        if isinstance(val[0], dict):
                            print(f"    First item keys: {list(val[0].keys())}")
                    elif isinstance(val, str) and len(val) > 50:
                        print(f"  Key '{key}' → string ({len(val)} chars) — may need another decode")
            elif isinstance(data, list):
                print(f"  List of {len(data)} items")
                if len(data) > 0:
                    first = data[0]
                    if isinstance(first, dict):
                        print(f"  First item type: dict")
                        print(f"  First item keys: {list(first.keys())}")
                    elif isinstance(first, str):
                        print(f"  First item type: string ({len(first)} chars)")
                        print(f"  First item preview: {first[:200]}")
                    else:
                        print(f"  First item type: {type(first).__name__}")
            print()

        except json.JSONDecodeError as e:
            print(f"Decode step {decode_step}: FAILED — {e}")
            print(f"  Data preview: {str(data)[:300]}")
            break

    # --- Step 3: Try to find the station list ---
    stations = None

    if isinstance(data, list):
        stations = data
    elif isinstance(data, dict):
        # Try common wrapper keys
        for key in data:
            val = data[key]
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                stations = val
                print(f"Found station list under key: '{key}' ({len(val)} items)")
                break
            elif isinstance(val, str):
                # Could be another layer of encoding
                try:
                    inner = json.loads(val)
                    if isinstance(inner, list) and len(inner) > 0:
                        stations = inner
                        print(f"Found station list under key '{key}' after extra decode ({len(inner)} items)")
                        break
                except:
                    pass

    if stations and len(stations) > 0:
        print(f"\n=== STATION LIST: {len(stations)} stations found ===")
        print(f"First station keys: {list(stations[0].keys())}")

        # Dump first 3 stations
        sample = stations[:3]
        print(f"\n=== FIRST 3 STATIONS (full detail) ===")
        print(json.dumps(sample, indent=2, default=str))

        # Save sample
        with open("alberta_raw_sample.json", "w") as f:
            json.dump(sample, f, indent=2, default=str)
        print(f"\nSaved to alberta_raw_sample.json")

        # --- Key analysis ---
        print(f"\n=== KEY ANALYSIS ===")
        all_keys = set()
        for s in stations:
            all_keys.update(s.keys())
        print(f"All unique keys across all stations ({len(all_keys)}):")
        for k in sorted(all_keys):
            # Sample the values
            sample_vals = []
            for s in stations[:5]:
                v = s.get(k)
                if v is not None:
                    sample_vals.append(str(v)[:60])
            print(f"  {k:<35} samples: {sample_vals[:3]}")

        # --- Look for station number candidates ---
        print(f"\n=== LIKELY STATION NUMBER FIELDS ===")
        import re
        wsc_pat = re.compile(r'\d{2}[A-Z]{2}\d{3}')
        for k in sorted(all_keys):
            matches = 0
            for s in stations[:50]:
                v = str(s.get(k, ""))
                if wsc_pat.search(v.upper()):
                    matches += 1
            if matches > 0:
                print(f"  '{k}' — {matches}/50 samples contain WSC-format IDs")

        # --- Station type field ---
        print(f"\n=== LIKELY STATION TYPE FIELDS ===")
        for k in sorted(all_keys):
            vals = set()
            for s in stations[:100]:
                v = s.get(k)
                if v is not None:
                    vals.add(str(v))
            if len(vals) <= 10 and len(vals) > 1:
                print(f"  '{k}' — unique values: {sorted(vals)}")

    else:
        print("\nCould not locate station list in the response.")
        print("Dumping full structure to alberta_raw_full.json ...")
        with open("alberta_raw_full.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("Saved. Please share this file for further analysis.")


if __name__ == "__main__":
    main()
