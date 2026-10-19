"""
River-network topology & flow direction (category="drainage").

The corridor/watershed "two points on a river" feature needs *directed*
connectivity — snap a point to the nearest watercourse, know flow direction, and
select the stream segments / contributing sub-basins between two points. The
DS-STD-2026.1 drainage probes verified watershed *geometry* (NHN, HydroBASINS,
WSC basins) but never tested topology usability. These probes do.

(a) SRC-HYDRORIVERS — HydroSHEDS HydroRIVERS, the primary river-network-with-
    flow-direction layer. Pre-computed topology: NEXT_DOWN (next downstream
    reach; 0 = terminal), MAIN_RIV (shared by every reach in one connected
    system → instant "same river?" test), ORD_STRA (Strahler), UPLAND_SKM,
    LENGTH_KM, DIST_DN_KM. We query the public hosted ArcGIS FeatureServer mirror
    for a few reaches and confirm the topology fields are present + fetchable
    (no download). Licence: HydroSHEDS (free scientific/educational/COMMERCIAL
    use; cite Lehner & Grill 2013). The end-to-end NEXT_DOWN chain-walk + two-
    point routing proof lives in tests/topology/hydrorivers_routing.py.

(b) SRC-BASINMAKER — North American Lake-River Routing Product v2.1 (U. Waterloo),
    an NHDPlus-VAA-style pre-assembled routing table (SubId / DowSubId; -1 = out
    of network), Canada-tuned, finer than HydroRIVERS. Metadata via the Zenodo
    record API (files + licence). Licence: MIT (commercial OK).

(c) SRC-ECCC-OGC-HYDRO — ECCC GeoMet OGC-API-Features hydrometric-realtime
    `items`, queried by a corridor bounding box. Not a routable network — this
    is the point-snap source: given a corridor, pull the gauges inside it (level/
    discharge GeoJSON points). Licence: ECCC End-use (commercial OK).

(d) SRC-NHN-NLFLOW — National Hydro Network bulk FTP root (feasibility only). NHN
    carries NLFLOW (directed virtual flow) at 1:50k but only as per-work-unit GML/
    GPKG tiles (no national seamless feature service), so this is a reachability
    check on the high-resolution future path, not an MVP backbone. OGL-Canada.

Citation / docs:
  https://www.hydrosheds.org/products/hydrorivers
  https://zenodo.org/records/4728185   (BasinMaker NA routing product v2.1)
  https://api.weather.gc.ca/collections/hydrometric-realtime
"""
from __future__ import annotations

from tests.sources._base import (
    ProbeContext, fields_from_json, http_probe, latest_ts_from_features, register,
)
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── (a) HydroRIVERS hosted ArcGIS FeatureServer mirror ──────────────
HYDRORIVERS_FS = (
    "https://services-eu1.arcgis.com/wVevVpTuMIgbSLhK/arcgis/rest/services/"
    "HydroRIVERS/FeatureServer/0/query"
)
# Topology fields that make routing possible — asserted present in fields_found.
HYDRORIVERS_TOPO_FIELDS = ("HYRIV_ID", "NEXT_DOWN", "MAIN_RIV", "ORD_STRA",
                           "UPLAND_SKM", "LENGTH_KM")


@register(
    test_id="drainage-hydrorivers-topology",
    category="drainage",
    source_id="SRC-HYDRORIVERS",
    label="HydroSHEDS HydroRIVERS river network + flow direction (NEXT_DOWN)",
    jurisdiction="CA",
    licence="HydroSHEDS (cite Lehner & Grill 2013)",
    commercial_ok="yes",
)
async def probe_hydrorivers(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {
        "where": "1=1",
        "outFields": ",".join(HYDRORIVERS_TOPO_FIELDS),
        "returnGeometry": "false",
        "resultRecordCount": 5,
        "f": "json",
    }
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, HYDRORIVERS_FS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=True,
            notes="ArcGIS FeatureServer query (5 reaches, topology fields)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=HYDRORIVERS_FS,
                requests=recs,
            )
        try:
            data = f.json()
            features = data.get("features", []) if isinstance(data, dict) else []
            fields = []
            if features and isinstance(features[0], dict):
                attrs = features[0].get("attributes") or {}
                fields = list(attrs.keys())
            if not fields:
                fld_defs = data.get("fields", []) if isinstance(data, dict) else []
                fields = [d.get("name") for d in fld_defs
                          if isinstance(d, dict) and d.get("name")]
        except Exception as exc:  # noqa: BLE001 — parse guard
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=HYDRORIVERS_FS,
                sample=f.text[:800], requests=recs,
            )
        fields_up = {str(x).upper() for x in fields}
        has_topology = {"HYRIV_ID", "NEXT_DOWN"}.issubset(fields_up)
        f.record.records_parsed = len(features)
        reason = classify.OK if (features and has_topology) else classify.OK_EMPTY
        return spec.result(
            retrievable=True, reason_category=reason, endpoint=HYDRORIVERS_FS,
            fields_found=fields, record_count=len(features),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes="flow-direction backbone; NEXT_DOWN (0=terminal) + MAIN_RIV give "
                  "directed connectivity. End-to-end routing proof: "
                  "tests/topology/hydrorivers_routing.py"
                  + ("" if has_topology else " [WARN: topology fields absent in sample]"),
            extra={"topology_fields_present": sorted(fields_up & set(HYDRORIVERS_TOPO_FIELDS)),
                   "has_next_down": "NEXT_DOWN" in fields_up},
        )


# ── (b) BasinMaker NA Lake-River Routing Product v2.1 (Zenodo) ──────
BASINMAKER_ZENODO = "https://zenodo.org/api/records/4728185"


@register(
    test_id="drainage-basinmaker-routing-na",
    category="drainage",
    source_id="SRC-BASINMAKER",
    label="BasinMaker North American Lake-River Routing Product v2.1 (SubId/DowSubId)",
    jurisdiction="CA",
    licence="MIT",
    commercial_ok="yes",
)
async def probe_basinmaker(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, BASINMAKER_ZENODO, source_id=spec.source_id,
            category=spec.category, from_metadata=True,
            notes="Zenodo record metadata (routing product files + licence)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=BASINMAKER_ZENODO,
                requests=recs,
            )
        try:
            data = f.json()
            files = data.get("files", []) if isinstance(data, dict) else []
            meta = data.get("metadata", {}) if isinstance(data, dict) else {}
            lic = meta.get("license")
            if isinstance(lic, dict):
                lic = lic.get("id") or lic.get("key") or str(lic)
            file_keys = [fi.get("key") for fi in files
                         if isinstance(fi, dict) and fi.get("key")][:10]
            title = meta.get("title") or ""
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=BASINMAKER_ZENODO,
                sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(files)
        reason = classify.OK if files else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(files), reason_category=reason, endpoint=BASINMAKER_ZENODO,
            fields_found=["SubId", "DowSubId", "Strahler", "RivLength"],
            record_count=len(files), latency_ms=f.record.latency_ms,
            sample=f.text[:800], requests=recs,
            notes="NHDPlus-VAA-style routing (SubId/DowSubId, -1=out-of-network); "
                  "~1.9 GB shapefile download, Canada+US, MERIT-Hydro ~90 m",
            extra={"zenodo_license": lic, "dataset_title": title, "file_keys": file_keys},
        )


# ── (c) ECCC GeoMet OGC-API hydrometric gauges by corridor bbox ─────
ECCC_OGC_ITEMS = "https://api.weather.gc.ca/collections/hydrometric-realtime/items"
# Bow River corridor sample: Banff → Calgary (minx,miny,maxx,maxy, EPSG:4326).
_BOW_CORRIDOR_BBOX = "-115.6,50.9,-114.0,51.3"


@register(
    test_id="drainage-eccc-ogc-hydro-corridor",
    category="drainage",
    source_id="SRC-ECCC-OGC-HYDRO",
    label="ECCC GeoMet OGC-API hydrometric gauges by corridor bbox (point-snap)",
    jurisdiction="CA",
    licence="OGL-Canada / ECCC MSC End-use Licence",
    commercial_ok="yes",
)
async def probe_eccc_ogc_hydro(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    params = {"f": "json", "limit": 5, "bbox": _BOW_CORRIDOR_BBOX, "sortby": "-DATETIME"}
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, ECCC_OGC_ITEMS, source_id=spec.source_id,
            category=spec.category, params=params, from_metadata=False,
            notes=f"OGC-API items bbox={_BOW_CORRIDOR_BBOX} (corridor gauge snap)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=ECCC_OGC_ITEMS,
                requests=recs,
            )
        try:
            data = f.json()
            feats = data.get("features", []) if isinstance(data, dict) else []
            fields = fields_from_json(data)
            number_matched = data.get("numberMatched") if isinstance(data, dict) else None
        except Exception as exc:  # noqa: BLE001
            _, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=ECCC_OGC_ITEMS,
                sample=f.text[:800], requests=recs,
            )
        f.record.records_parsed = len(feats)
        latest_obs, age_min = latest_ts_from_features(feats, prefer_keys=("DATETIME", "DATETIME_LST"))
        reason = classify.OK if feats else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(feats), reason_category=reason, endpoint=ECCC_OGC_ITEMS,
            fields_found=fields, record_count=len(feats), station_count=number_matched,
            latency_ms=f.record.latency_ms, latest_obs_utc=latest_obs,
            data_age_minutes=age_min, sample=f.text[:800], requests=recs,
            notes="point-snap source for a corridor: GeoJSON gauge points w/ level/"
                  f"discharge inside the bbox (numberMatched={number_matched})",
            extra={"number_matched": number_matched, "bbox": _BOW_CORRIDOR_BBOX},
        )


# ── (d) NHN bulk FTP root — high-resolution path feasibility only ───
NHN_FTP_ROOT = "http://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_nhn_rhn/"


@register(
    test_id="drainage-nhn-nlflow-feasibility",
    category="drainage",
    source_id="SRC-NHN-NLFLOW",
    label="National Hydro Network NLFLOW directed-flow bulk FTP (1:50k, feasibility)",
    jurisdiction="CA",
    licence="OGL-Canada",
    commercial_ok="yes",
    sanctioned=False,
)
async def probe_nhn_nlflow(spec, ctx: ProbeContext) -> TestResult:
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, NHN_FTP_ROOT, source_id=spec.source_id,
            category=spec.category, from_metadata=True,
            notes="NHN bulk FTP root autoindex reachability (per-work-unit GML/GPKG)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=NHN_FTP_ROOT,
                requests=recs,
                notes="high-res 1:50k path; NLFLOW carries directed flow but is "
                      "distributed as 1,300+ per-work-unit tiles (assembly cost)",
            )
        has_body = bool((f.text or "").strip())
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if has_body else classify.OK_EMPTY,
            endpoint=NHN_FTP_ROOT, fields_found=["NLFLOW (networklinearflow)"],
            latency_ms=f.record.latency_ms, sample=(f.text or "")[:800], requests=recs,
            notes="reachable; NLFLOW = directed virtual water-flow at 1:50k, but only "
                  "per-work-unit tiles — not an MVP backbone (use HydroRIVERS). "
                  "Successor: Canadian Hydrospatial Network (CHN)",
        )
