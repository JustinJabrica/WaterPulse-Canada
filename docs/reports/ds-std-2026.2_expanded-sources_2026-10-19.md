# WaterPulse Data-Source Standard — DS-STD-2026.2: Expanded Sources & Fetch-Testing

**Status:** addendum to DS-STD-2026.1 · **Run date:** 2026-10-19 · **Author:** WaterPulse engineering

> This report extends **DS-STD-2026.1** (the 2026-09-16 recon / test-suite / results /
> implementation-spec set in this folder). It adds and *live-tests* the data categories the
> product vision needs but 2026.1 did not cover, re-confirms the 2026.1 baseline, and resolves
> the previously-deferred commercial-licensing posture. Scope this round is **data sourcing +
> fetch-testing only** — no app ingestion or UI was built.

## 1. Why this round exists

WaterPulse's goal: a user drops **two points on a river** and sees **conditions** (level/flow,
water quality/pollution, water temperature, weather/AQI), **warnings** (flood), and
**predictions** (flood) for the **whole corridor/watershed between those points**, Canada-wide —
plus derived reads (recreation suitability; historical-trend & causal insight). DS-STD-2026.1
verified 98/102 hydrometric/weather/environment probes but had three gaps against this vision:

1. **No water-quality / pollution category.**
2. **River-network flow-direction / topology never tested** — only static watershed geometry.
3. **No national flood-warning / streamflow-forecast / radar-precip / tides / wildfire-smoke probes.**

This round closes all three and adds a deep, end-to-end topology routing proof.

## 2. What was added to the probe suite

17 new probes across 3 new categories (`waterquality`, `tides`, `wildfire`) and extensions to
`drainage`, `precip`, `flood`. All follow the established `tests/sources/*.py` + `@register(...)`
pattern (auto-discovered by `tests/matrix.py`). New/changed files:

| File | Adds |
|---|---|
| `tests/sources/_geomet.py` | shared GeoMet WMS GetCapabilities layer-grep helper (extracted from `flood.py`) |
| `tests/sources/_datastream.py` | DataStream OData v4 config + `WP_DATASTREAM_API_KEY` → `x-api-key` |
| `tests/sources/water_quality.py` | ECCC WQMS, DataStream-WQ, ON PWQMN, BC EnMoDS, QC IQBP, AB RWQI |
| `tests/sources/river_network.py` | HydroRIVERS, BasinMaker, ECCC OGC-API gauges, NHN NLFLOW (residual) |
| `tests/sources/precip.py` | ECCC radar, HRDPA precip analysis, lightning (GeoMet WMS) |
| `tests/sources/tides.py` | DFO/CHS IWLS water levels |
| `tests/sources/wildfire.py` | CWFIS active-fire hotspots, ECCC FireWork smoke |
| `tests/sources/flood.py` | + ECCC CAP national weather/flood alerts |
| `tests/topology/hydrorivers_routing.py` | deep corridor-routing proof (not a sanctioned probe) |

Matrix after: **123 probes** (118 sanctioned + 5 residual) across 15 categories — up from 106.

## 3. Live fetch-test results (2026-10-19)

All 17 new probes were exercised live. **16/17 retrievable; the 1 non-retrievable is the
documented, by-design DataStream key gate** (HTTP 401 without `WP_DATASTREAM_API_KEY`).

### 3.1 Water quality / pollution (new category)
| source | verdict | evidence | licence | commercial |
|---|---|---|---|---|
| SRC-ECCC-WQMS *(backbone #1)* | **OK** | CKAN "National Long-term Water Quality Monitoring Data"; formats CSV/ESRI REST/HTML/TXT/WMS; keyless CSV on ECCC data mart | OGL-Canada | **yes** |
| SRC-DATASTREAM-WQ *(backbone #2)* | **401 (key required)** | OData v4 Observations; documented keyless 401; `WP_DATASTREAM_API_KEY` unblocks | per-dataset ODC-By/PDDL/OGL | conditional (all commercial-OK w/ attribution+DOI) |
| SRC-ON-PWQMN | OK | CKAN metadata (1964–present) | OGL-Ontario | yes |
| SRC-BC-ENMODS | OK | CKAN metadata (EMS retired 2026-03; EnMoDS successor) | OGL-BC | yes |
| SRC-QC-IQBP | OK | CKAN metadata; CSV/GeoJSON/ESRI REST | CC-BY 4.0 | yes |
| SRC-AB-RWQI | OK | CKAN metadata (28 LTRN sites, monthly) | OGL-Alberta | yes |

Reality check: Canadian WQ is **lab grab-samples, not live sondes** — model it as "latest sample +
trend." Swim-safety parameters (E. coli / fecal coliform, turbidity, cyanobacteria/HAB) are
per-dataset fields, strongest via DataStream + QC IQBP.

### 3.2 River-network topology / flow direction (drainage extension)
| source | verdict | evidence | licence | commercial |
|---|---|---|---|---|
| SRC-HYDRORIVERS | **OK (fields)** | ArcGIS mirror returns topology fields HYRIV_ID/NEXT_DOWN/MAIN_RIV/ORD_STRA/UPLAND_SKM/LENGTH_KM. **Caveat: the public `services-eu1` mirror carries only a regional (Africa) subset and rejects spatial queries** — North America must come from the regional file (§4). | HydroSHEDS (cite Lehner & Grill 2013) | yes |
| SRC-BASINMAKER | OK | Zenodo record 4728185 metadata; MIT; SubId/DowSubId routing (Canada+US, ~1.9 GB) | MIT | yes |
| SRC-ECCC-OGC-HYDRO | OK | `hydrometric-realtime/items?bbox=` returns GeoJSON gauge points w/ LEVEL/DISCHARGE (point-snap source). *Verify bbox tightness at ingestion — matched count was large.* | OGL-Canada / ECCC | yes |
| SRC-NHN-NLFLOW | residual (not run) | 1:50k directed flow, per-work-unit tiles only — future high-res path | OGL-Canada | yes |

### 3.3 Flood / alerts (flood extension)
| source | verdict | evidence | licence | commercial |
|---|---|---|---|---|
| SRC-ECCC-CAP | **OK** | Datamart CAP alerts autoindex reachable (CAP 1.2 XML; national rainfall/flood/thunderstorm warnings) | OGL-Canada / ECCC | yes |

Streamflow-forecast note (carried from research): **no public national streamflow-forecast API
exists.** ECCC's DHPS (1 km river-discharge routing, 6-day) and NSRPS are withheld as point/reach
services and appear only as **raster** WMS/GRIB2 (point value via WMS GetFeatureInfo/WCS). The
existing `flood-eccc-waterpred` probe already enumerates the DHPS/WCPS/OHPS WMS layers. Implication:
corridor flood *prediction* must come from official provincial feeds + our own heuristic now, a real
model later — exactly the approved phased plan.

### 3.4 Precipitation / storm (precip extension) — ECCC GeoMet WMS
| source | verdict | layers matched | commercial |
|---|---|---|---|
| SRC-ECCC-RADAR | **OK** | RADAR_1KM rain/snow rate | yes |
| SRC-ECCC-HRDPA | **OK** | HRDPA 2.5 km precip analysis (CaPA) | yes |
| SRC-ECCC-LIGHTNING | **OK** | Lightning 2.5 km density | yes |

### 3.5 Tides (new category)
| source | verdict | evidence | commercial |
|---|---|---|---|
| SRC-CHS-IWLS | **OK** | DFO/CHS IWLS `/api/v1/stations` → 1,576 water-level stations (wlo/wlp); clean per-station JSON, point-queryable | yes (OGL-Canada) |

### 3.6 Wildfire & smoke (new category)
| source | verdict | evidence | commercial |
|---|---|---|---|
| SRC-CWFIS-FIRE | **OK** | WFS GeoJSON `hotspots_last24hrs` (point-queryable; 0 rows is normal off fire season) | yes (OGL-Canada) |
| SRC-ECCC-FIREWORK | **OK** | GeoMet WMS RAQDPS-FW PM2.5 smoke forecast layers | yes (ECCC) |

### 3.7 Full sanctioned-suite refresh (baseline re-confirmation)

Full run `probes-20261019T102713Z` (118 sanctioned probes, downloads on): **113/118 retrievable in
415.3 s**. `commercial_ok` tally: **yes 111, non-commercial 3, conditional 2, unknown 2**.

**Zero regressions vs. the 2026.1 baseline (98/102).** The 5 non-retrievable are all known/expected:

| reason | count | sources | status |
|---|---|---|---|
| `dns_error` | 3 | GSC SensorThings groundwater (`mon.geosciences.ca`) | pre-existing (identical to 2026.1); 3 other groundwater sources cover it |
| `http_401` | 2 | DataStream RivTemp + DataStream-WQ | documented key gate; set `WP_DATASTREAM_API_KEY` to unblock |

Net: +16 sanctioned probes over 2026.1 (102→118), +15 retrievable (98→113) — i.e. **all 16 new
sanctioned probes behaved as designed** (15 OK + 1 documented DataStream 401), and no previously-
passing probe broke. Retrievable-by-category: current 30, historical 19, stations 15, drainage 9,
precip 8, flood 7, waterquality 5, weather 5, groundwater 3, ice 3, snow 3, aqi 2, wildfire 2,
tides 1, watertemp 1. (The `SRC-NHN-NLFLOW` residual probe is excluded from the sanctioned run.)

## 4. Deep topology proof — "two points → corridor" is computable

`tests/topology/hydrorivers_routing.py` loads the **North-America HydroRIVERS regional
shapefile** (`HydroRIVERS_v10_na_shp.zip`, 66 MB zip → 986,463 reaches; EPSG:4326; read with
pure-Python `pyshp`, no GDAL) and routes a real corridor. Result (Bow River, Banff → Calgary):

```
[load]   986,463 North-America HydroRIVERS reaches
[snap]   Banff   -> reach 70212715 (743 m)   MAIN_RIV=70045262  DIST_DN_KM=2981.5  ORD_STRA=2
[snap]   Calgary -> reach 70217104 (1049 m)  MAIN_RIV=70045262  DIST_DN_KM=2831.8  ORD_STRA=4
[same river system?]  True  (shared MAIN_RIV)
[corridor]  35 reaches linked by NEXT_DOWN; length |ΔDIST_DN_KM| ≈ 149.7 km
[chain]     NEXT_DOWN terminates at outlet (0) after 644 hops
=> PASS
```

**Conclusion:** snap-to-river, flow direction, same-system test, segment-selection between two
points, and outlet termination are all computable from fetchable, commercial-OK data. **HydroRIVERS
is the recommended flow-direction backbone**; join corridor reaches to **HydroBASINS level-12** (via
`HYBAS_L12`) for the contributing sub-basin polygons (the corridor/watershed selection).

## 5. Source → surface matrix (ad-supported vs ad-free)

Monetization is confirmed (ad-supported, local + possibly Google Ads). Per direction, licensing is
**not** a sourcing filter: we keep every reliable source and let `commercial_ok` govern **where**
data appears. Non-commercial/conditional data surfaces on **ad-free** pages (keeping that usage
non-commercial); commercial-OK data can appear on **ad-supported** pages. **Every capability has a
commercial-OK option, so no ad-supported surface is starved.**

| Capability | Commercial-OK primary (ad-supported OK) | Non-commercial / conditional (ad-free) |
|---|---|---|
| Hydrometric realtime | ECCC Datamart/GeoMet (national) | AB portal, SK WSA, BC AQUARIUS (scrape) |
| Hydrometric history | HYDAT, ECCC GeoMet daily/monthly | — |
| Weather | **MET Norway + ECCC CityPage** | Open-Meteo (free tier) |
| AQI | **ECCC AQHI** | Open-Meteo AQI (US-AQI scale) |
| Water quality | ECCC WQMS + provincial OGL/CC-BY | DataStream (per-dataset; mostly commercial-OK) |
| Water temperature | NL ADRS, CIOOS, embedded gauge fields | RivTemp via DataStream (key) |
| Flood warnings | ECCC CAP, BC RFC, QC Vigilance | Conservation ON, MB HFC (`unknown`) |
| Flood/streamflow prediction | ECCC DHPS/WCPS/OHPS (raster) | — (no public point API) |
| River topology / flow dir. | HydroRIVERS, HydroBASINS, BasinMaker, NHN | — |
| Precip / radar / lightning | ECCC GeoMet (radar/HRDPA/lightning) | — |
| Tides | CHS IWLS | — |
| Wildfire / smoke | CWFIS, ECCC FireWork | — |
| Snow / ice / groundwater | CanSWE, BC ASWS, CRID, GIN, PGMN, RSESQ | — |

**Weather/AQI decision (resolving the 2026.1 deferral):** adopt **MET Norway + ECCC AQHI + ECCC
CityPage** as the commercial-OK stack for ad-supported surfaces; keep **Open-Meteo** (richer
variables) on ad-free surfaces, or take **Open-Meteo's paid/commercial API tier** to use its full
variable set everywhere under a commercial licence.

## 6. Recommendations / next steps

1. **Adopt HydroRIVERS + HydroBASINS L12 as the corridor/flow-direction backbone** (ingest the NA
   regional files; BasinMaker as a finer Canada-tuned upgrade later). Snap gauges + conditions to
   reaches; select sub-basins between two points via `NEXT_DOWN`/`PFAF_ID`.
2. **Obtain the free DataStream `x-api-key`** (requested) to unblock live water-quality + river-temp
   pulls; ECCC WQMS remains the keyless national backbone.
3. **Wire the national CAP alert layer** (ECCC) as the uniform flood/weather-warning feed spanning
   the gap between the 5 provincial flood services.
4. **Phase flood prediction:** official feeds (BC RFC / QC Vigilance / ECCC water-prediction rasters)
   → our heuristic (percentile rating + trend + HRDPA/QPF + snow) → a real model. No public national
   streamflow-forecast API to ingest today.
5. **Capture historical depth + weather↔water co-location per source** (recorded in the suite) — the
   evidence base for the downstream recreation-index and trend/causal-analytics features.
6. **Honour the source→surface matrix** in the app: `commercial_ok` drives ad placement, not source
   exclusion.

## 7. How to reproduce

```bash
# full sanctioned suite (inside the backend container; or any env with httpx)
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources
# new categories only
#   --category waterquality | tides | wildfire | precip | flood | drainage
# with a DataStream key:
#   -e WP_DATASTREAM_API_KEY=<key>   (docker)  /  WP_DATASTREAM_API_KEY=<key> … (local)
# deep topology proof (needs pyshp + the NA HydroRIVERS .shp):
python -m tests.topology.hydrorivers_routing /path/to/HydroRIVERS_v10_na.shp
```
Evidence lands under `waterpulse-backend/tests/logs/<run_id>/` (requests.csv, tests.csv,
coverage.csv, coverage_summary.json, per-test JSON).
