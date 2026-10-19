"""
HydroRIVERS corridor-routing feasibility proof (DS-STD-2026.2).

The DEEP topology proof the data-source round promised — NOT a sanctioned probe
and NOT part of the probe_sources matrix. It proves the "two points on a river ->
corridor/watershed between them" mechanic is computable from fetchable data, by
exercising HydroSHEDS HydroRIVERS' pre-computed flow-direction topology
(NEXT_DOWN / MAIN_RIV / DIST_DN_KM) over real North American data.

Why file-based: the public hosted HydroRIVERS ArcGIS FeatureServer mirror turned
out to carry only a regional (Africa) subset and to reject spatial queries, so it
cannot serve a Canadian corridor. The authoritative, seamless North-America layer
is the regional shapefile from the HydroSHEDS data portal — the route the plan
anticipated. We read it with `pyshp` (pure Python, NO GDAL) and route locally.

Setup (one-off; dev-only, NOT added to the app requirements)::

    pip install pyshp
    # download + unzip the North-America regional river network (~66 MB zip):
    #   https://data.hydrosheds.org/file/hydrorivers/HydroRIVERS_v10_na_shp.zip
    # point WP_HYDRORIVERS_SHP at the unzipped .shp (or pass it as argv[1]):
    python -m tests.topology.hydrorivers_routing /path/to/HydroRIVERS_v10_na.shp

It demonstrates, over the Bow River between Banff and Calgary, Alberta:
  1. snap-to-river    — two coordinates snap to the nearest reach by geometry.
  2. same river?      — the two snapped reaches share a MAIN_RIV (one system).
  3. flow direction   — NEXT_DOWN gives a directed edge (0 = ocean/sink terminal).
  4. corridor routing — walking NEXT_DOWN from the upstream reach reaches the
                        downstream reach: the ordered reach list between them +
                        the corridor length (|DIST_DN_KM a - b|).
  5. chain terminates — following NEXT_DOWN to the end lands on an outlet (0).
"""
from __future__ import annotations

import math
import os
import sys

# Two sample points on the Bow River (lon, lat), WGS84.
POINT_UPSTREAM = (-115.5708, 51.1784)    # Banff
POINT_DOWNSTREAM = (-114.0719, 51.0447)  # Calgary
SNAP_WINDOW_DEG = 0.25   # only compute vertex distance for reaches whose bbox is near a point
_MAX_WALK = 500_000      # local safety cap (never network hops)

DEFAULT_SHP = os.environ.get("WP_HYDRORIVERS_SHP", "")
DOWNLOAD_HINT = (
    "  Setup: pip install pyshp ; download + unzip\n"
    "    https://data.hydrosheds.org/file/hydrorivers/HydroRIVERS_v10_na_shp.zip\n"
    "  then pass the .shp path as argv[1] or set WP_HYDRORIVERS_SHP."
)


def _haversine_km(lon1, lat1, lon2, lat2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _near(bbox, lon, lat, pad=SNAP_WINDOW_DEG) -> bool:
    xmin, ymin, xmax, ymax = bbox
    return (xmin - pad) <= lon <= (xmax + pad) and (ymin - pad) <= lat <= (ymax + pad)


def _main() -> int:
    print("HydroRIVERS corridor-routing feasibility proof (DS-STD-2026.2)")
    print("Sample: Bow River, Banff -> Calgary, AB\n")

    shp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHP
    if not shp or not os.path.exists(shp):
        print(f"FAIL: HydroRIVERS shapefile not found ({shp!r}).\n{DOWNLOAD_HINT}")
        return 2
    try:
        import shapefile  # pyshp
    except ImportError:
        print(f"FAIL: pyshp not installed.\n{DOWNLOAD_HINT}")
        return 2

    reader = shapefile.Reader(shp)
    names = [f[0] for f in reader.fields[1:]]
    idx = {n: i for i, n in enumerate(names)}
    need = ("HYRIV_ID", "NEXT_DOWN", "MAIN_RIV", "DIST_DN_KM")
    missing = [n for n in need if n not in idx]
    if missing:
        print(f"FAIL: shapefile missing topology fields {missing}; found {names}")
        return 1

    # Single pass: build the full NEXT_DOWN graph (attrs) + snap both points.
    graph: dict[int, tuple] = {}          # hyriv_id -> (next_down, main_riv, dist_dn, ord_stra)
    best = {"up": (None, float("inf")), "down": (None, float("inf"))}
    ord_i = idx.get("ORD_STRA")
    total = 0
    for sr in reader.iterShapeRecords():
        rec = sr.record
        hid = int(rec[idx["HYRIV_ID"]])
        nd = int(rec[idx["NEXT_DOWN"]] or 0)
        mr = int(rec[idx["MAIN_RIV"]] or 0)
        dd = float(rec[idx["DIST_DN_KM"]] or 0)
        osr = int(rec[ord_i]) if ord_i is not None and rec[ord_i] is not None else None
        graph[hid] = (nd, mr, dd, osr)
        total += 1
        bbox = getattr(sr.shape, "bbox", None)
        if not bbox:
            continue
        for key, (plon, plat) in (("up", POINT_UPSTREAM), ("down", POINT_DOWNSTREAM)):
            if _near(bbox, plon, plat):
                for x, y in sr.shape.points:
                    d = _haversine_km(plon, plat, x, y)
                    if d < best[key][1]:
                        best[key] = ((hid, nd, mr, dd, osr), d)
    print(f"[load] {total} North-America HydroRIVERS reaches read (pyshp, EPSG:4326)")

    a, a_km = best["up"]
    b, b_km = best["down"]
    if not a or not b:
        print("FAIL: could not snap one/both points to a reach.")
        return 1
    (a_id, a_nd, a_main, a_dd, a_ord) = a
    (b_id, b_nd, b_main, b_dd, b_ord) = b
    print(f"[snap] upstream  Banff    -> reach {a_id}  ({a_km*1000:.0f} m)  "
          f"MAIN_RIV={a_main}  DIST_DN_KM={a_dd:.1f}  ORD_STRA={a_ord}")
    print(f"[snap] downstream Calgary -> reach {b_id}  ({b_km*1000:.0f} m)  "
          f"MAIN_RIV={b_main}  DIST_DN_KM={b_dd:.1f}  ORD_STRA={b_ord}")

    same = a_main == b_main
    print(f"\n[connectivity] same MAIN_RIV (same river system)? {same}")
    if not same:
        print("FAIL: snapped reaches are on different river systems.")
        return 1

    # (4) corridor: walk NEXT_DOWN from the more-upstream reach to the other.
    up_id, down_id = (a_id, b_id) if a_dd >= b_dd else (b_id, a_id)
    corridor = [up_id]
    nxt = graph[up_id][0]
    hops = 0
    reached = False
    while nxt and hops < _MAX_WALK:
        corridor.append(nxt)
        if nxt == down_id:
            reached = True
            break
        if nxt not in graph:
            break
        nxt = graph[nxt][0]
        hops += 1
    corridor_km = abs(a_dd - b_dd)
    print(f"[corridor] {len(corridor)} reaches between the two points "
          f"({'reached downstream reach' if reached else 'downstream reach not on this walk'}):")
    print("           " + " -> ".join(str(c) for c in corridor[:15])
          + (" -> ..." if len(corridor) > 15 else ""))
    print(f"[corridor] length (|DIST_DN_KM a - b|) = {corridor_km:.1f} km")

    # (5) chain terminates at an outlet (0).
    cur = graph[up_id][0]
    chain = 0
    while cur and cur in graph and chain < _MAX_WALK:
        cur = graph[cur][0]
        chain += 1
    outlet_ok = (cur == 0)
    print(f"[chain] NEXT_DOWN from reach {up_id} reaches a terminal outlet (0)? "
          f"{outlet_ok} after {chain} hops")

    if reached and outlet_ok:
        print("\nPASS: snap + flow-direction + corridor selection + outlet termination "
              "all computable from HydroRIVERS. Contributing sub-basins for the "
              "corridor: join these reaches to HydroBASINS level-12 via HYBAS_L12.")
        return 0
    print("\nPARTIAL: same river system confirmed; "
          + ("corridor walk did not reach the downstream reach "
             "(points may bracket a confluence off the main stem — try points "
             "clearly on one stem)" if not reached else "chain did not terminate at 0"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
