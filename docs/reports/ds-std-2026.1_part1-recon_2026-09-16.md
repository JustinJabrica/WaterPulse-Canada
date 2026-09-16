# WaterPulse Data-Source Standard (DS-STD-2026.1) — Part 1: Standard & Reconnaissance

**Report ID:** DS-STD-2026.1
**Part:** 1 of 3 — Standard & Reconnaissance
**Version:** 1.0
**Status:** Draft
**Publication date:** 2026-09-16
**Prepared for:** WaterPulse-Canada
**Authoring organization:** WaterPulse Data Engineering
**Persistent identifier (PID):** TBD (placeholder)

**How to cite:** WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1," 2026-09-16.

---

## Abstract

This document is Part 1 of the WaterPulse Data-Source Standard (DS-STD-2026.1), a citable technical
standard governing the acquisition, validation, licensing, and attribution of hydrometric and allied
environmental data for WaterPulse-Canada, a public-good, currently non-commercial river-data
application covering all thirteen Canadian provinces and territories. Part 1 defines the normative
architecture, enumerates the data-source registry, provides per-source datasheets, and states the
usage-rights and monetization posture. The core architectural position is a *primary/backup* model:
for each jurisdiction the **primary** feed SHALL be that jurisdiction's own authoritative programmatic
source where one exists, and the **backup/validation** layer SHALL be Environment and Climate Change
Canada (ECCC) and the Water Survey of Canada (WSC) — the Meteorological Service of Canada (MSC)
Datamart real-time bulk CSV, the HYDAT deeply validated historical archive, the GeoMet OGC API
(metadata plus daily/monthly/annual historical products), City Page weather, the Air Quality Health
Index (AQHI), and climate observations. Only about six of thirteen provinces/territories expose a
genuine programmatic provincial river feed (Alberta, British Columbia in part, Manitoba, Ontario,
Quebec, and Newfoundland and Labrador; Saskatchewan values are scrape-only); the remainder are
ECCC-primary. Quebec is an explicit exception: ECCC carries only about fifteen Quebec real-time
stations, so Quebec is treated as provincial-only (Vigilance). HYDAT and GeoMet constitute the
historical backbone.

All quantitative claims in this Part are grounded in a single measured reconnaissance run,
`run_id=probes-20260916T090344Z` (2026-09-16), in which **80 of 86 sanctioned probes were retrievable
in 186.7 s** across a registry of 90 probes (86 sanctioned + 4 residual) spanning 12 categories.
Measured figures are labelled as such and are distinguished throughout from advertised figures.

## Index Terms

Air Quality Health Index (AQHI); attribution; Canada; data licensing; data provenance; Datamart;
ECCC; Environment and Climate Change Canada; GeoMet; HYDAT; hydrometric data; monetization; OGC API;
Open Government Licence; open data; provenance; provincial water data; reconnaissance; river data;
Water Survey of Canada (WSC); WaterPulse.

## RFC 2119 Note

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT",
"RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119
[43], and only when they appear in **UPPERCASE**. Normative requirements appear principally in
Sections 2 (Conformance), 10 (Usage Rights, Licensing & Monetization), and 11 (Attribution & Citation
Requirements). All other sections are informative unless a sentence uses an RFC-2119 keyword.

---

## 1. Front Matter

This Part is a self-contained normative and descriptive instrument. It establishes the identity of the
standard, the reconnaissance evidence base, the source registry, the datasheets, and the licensing
matrix. Parts 2 and 3 build on this Part and SHALL NOT be read as superseding the normative clauses
herein except where they explicitly amend a numbered clause of this Part.

- **Report ID:** DS-STD-2026.1
- **Version:** 1.0
- **Status:** Draft
- **Publication date:** 2026-09-16
- **Prepared for:** WaterPulse-Canada
- **Authoring organization:** WaterPulse Data Engineering
- **Persistent identifier:** TBD (placeholder; a DOI or w3id-class PID SHALL be minted before the
  standard leaves Draft status — see Section 16).

**Document set.** DS-STD-2026.1 is published in three Parts:

| Part | Title | Scope |
|------|-------|-------|
| 1 | Standard & Reconnaissance | This document: architecture, registry, datasheets, coverage, cadence, QA/QC, licensing matrix, risk register, references. |
| 2 | (see Part 2) | Companion Part; not duplicated here. |
| 3 | (see Part 3) | Companion Part, including the dated residual-harness overnight addendum. |

**Measurement provenance for this Part.** Unless a figure is explicitly labelled *advertised*, every
station count, record count, field count, latency, licence flag, and retrievability result in this
Part is drawn verbatim from reconnaissance run `probes-20260916T090344Z` and its `coverage.csv`
output. That run is the single normative evidence base for Part 1.

---

## 2. Introduction, Scope, Audience, Posture & Conformance

### 2.1 Introduction

WaterPulse-Canada aggregates near-real-time river conditions (water level, discharge, water
temperature), historical hydrometric records, and a supporting envelope of drainage, groundwater,
flood, precipitation, snow, ice, weather, and air-quality data for the Canadian public. Because the
underlying data are produced by many independent publishers — one federal department, thirteen
provincial/territorial governments, several federal agencies, and a small number of international and
academic providers — the application's integrity depends on a disciplined, auditable understanding of
*which source is authoritative for what*, *under what licence*, *at what cadence and quality*, and
*with what reliability*. This standard captures that understanding as a citable instrument.

### 2.2 Scope

This standard covers:

1. the identification and role assignment (primary / backup / enrichment) of every data source in the
   WaterPulse ingestion registry;
2. the technical contract of each source (endpoints, API version, formats, fields, units, datum, CRS,
   pagination, quirks);
3. the spatial and temporal coverage actually observed;
4. update cadence, latency, and data-quality/QA-QC semantics;
5. provenance, lineage, and versioning expectations;
6. usage rights, licensing, attribution, and monetization posture (normative);
7. privacy, security, reliability, retention, change-management, and risk.

This standard does **not** specify application UI, database schema internals, or deployment topology,
except where those touch data provenance or attribution obligations.

### 2.3 Intended audience

- **Data engineers** integrating or maintaining ingestion connectors.
- **Legal/compliance reviewers** assessing redistribution and commercial exposure.
- **Product and partnership stakeholders** evaluating a future commercial tier.
- **External auditors and citators** who need a stable, referenceable description of the data supply
  chain.

### 2.4 Relationship to the project's non-commercial posture and commercial path

WaterPulse-Canada is presently operated as a non-commercial public good. This standard is written to
serve **two postures simultaneously and without discarding any source**:

- **Posture A — non-commercial (current).** Every source in the registry is usable, subject to
  attribution and technical-limit compliance. No source is excluded.
- **Posture B — hypothetical commercial tier (future).** The registry is re-scored against each
  upstream's commercial terms. As established normatively in Section 10, a commercial tier is capped by
  the **most-restrictive upstream term**. The binding blockers are **Alberta** (rivers.alberta.ca,
  Government of Alberta copyright, written permission required) and **Saskatchewan** (WSA, Crown
  copyright, written permission required), plus the **Open-Meteo free tier** (non-commercial only;
  commercial use requires a paid plan or substitution by ECCC City Page or MET Norway). All other
  sources are commercial-OK with attribution.

The project licence (how WaterPulse licenses its own compiled product and code) SHALL be kept
conceptually and legally **separate** from each upstream data licence; Section 10 treats them
distinctly.

### 2.5 Conformance

An ingestion pipeline, deployment, or downstream redistribution **conforms** to DS-STD-2026.1 Part 1
if and only if it satisfies all of the following:

- **C-1.** Every ingested source SHALL be represented by a registry entry (Section 4) carrying its
  Source ID, publisher, role, category, and current status.
- **C-2.** For each jurisdiction, the pipeline SHALL honour the primary/backup role assignment of
  Section 4 and the datasheets of Section 5, including the Quebec exception (ECCC carries only ~15 QC
  real-time stations; QC is provincial-only via Vigilance).
- **C-3.** Every rendered or redistributed datum SHALL carry the attribution string mandated for its
  source in Section 10/11.
- **C-4.** The pipeline SHALL NOT exceed a source's stated technical limits (Section 10), including the
  ECCC acceptable-use ceiling (contact MSC at or above roughly 86,400 requests/day, i.e. ~1 req/s),
  the prohibition on cache-bypass headers against ECCC endpoints, and per-provider rate limits.
- **C-5.** A deployment claiming commercial conformance (Posture B) SHALL additionally satisfy the
  composite most-restrictive analysis of Section 10.6 — in particular it SHALL NOT surface Alberta or
  Saskatchewan values commercially without written permission, and SHALL NOT use the Open-Meteo free
  tier commercially.
- **C-6.** Provisional (real-time) values SHALL be visually or semantically distinguished from
  validated (HYDAT) values wherever both are presented (Section 8).

A deployment MAY exceed these requirements. A deployment that violates any of C-1 through C-6 is
**non-conforming** and SHALL NOT be described as compliant with DS-STD-2026.1.

---

## 3. Definitions, Acronyms & Data-Flow Reference Model

### 3.1 Definitions

- **Source (Source ID).** A distinct upstream data service identified by a `SRC-*` identifier. A
  source MAY be probed across multiple jurisdictions; each jurisdictional probe is counted separately
  in the probe registry (Section 4).
- **Probe.** A single measured retrieval of one source for one jurisdiction/product in the
  reconnaissance run. The registry contains 90 probes across 40 distinct Source IDs.
- **Sanctioned probe.** A probe that is part of the standard, polite, non-scraping acquisition path.
  There are 86 sanctioned probes.
- **Residual probe.** A harness-only probe (scrape or stress path) not part of the sanctioned path.
  There are 4 residual probes (Section 4.3).
- **Primary source.** The authoritative programmatic feed for a jurisdiction's core river data.
- **Backup / validation source.** ECCC/WSC feeds used to cross-check, backfill, and validate primary
  data; the sole feed where no provincial programmatic feed exists.
- **Enrichment source.** A source supplying supporting context (drainage, groundwater, flood, snow,
  ice, weather, air quality, water temperature) rather than the core river signal.
- **Provisional value.** A real-time or near-real-time reading not yet quality-assured.
- **Validated value.** A quality-assured reading published in HYDAT.
- **Retrievable.** A probe returned a usable response (HTTP success and parseable payload) in the run.
- **`ok_empty`.** The endpoint was reachable and returned success but the light sample yielded no rows
  or no file link; the source is retrievable but requires a deeper query.

### 3.2 Acronyms

| Acronym | Expansion |
|---------|-----------|
| AGOL | ArcGIS Online |
| AQHI | Air Quality Health Index |
| ADRS | (NL) Advanced Data Retrieval System |
| ASWS | (BC) Automated Snow Weather Stations |
| CaPA / RDPA | Canadian / Regional Deterministic Precipitation Analysis |
| CIOOS | Canadian Integrated Ocean Observing System |
| CIS | Canadian Ice Service |
| CRID | Canadian River Ice Database |
| CRS | Coordinate Reference System |
| ECCC | Environment and Climate Change Canada |
| EDR | (OGC API) Environmental Data Retrieval |
| ERA5 | ECMWF Reanalysis v5 |
| FHIMP | Flood Hazard Identification and Mapping Program (NRCan) |
| FOIP | Freedom of Information and Protection of Privacy (Alberta) |
| FWA | (BC) Freshwater Atlas |
| GIN | Groundwater Information Network |
| GRHQ | (QC) Géobase du réseau hydrographique du Québec |
| GSC | Geological Survey of Canada |
| HYDAT | National Water Data Archive (WSC) |
| KiWIS | Kisters Web Interoperability Solution (WISKI API) |
| MSC | Meteorological Service of Canada |
| NHN | National Hydro Network |
| NHP | National Hydrometric Program |
| OGC | Open Geospatial Consortium |
| OGL | Open Government Licence |
| PGMN | (ON) Provincial Groundwater Monitoring Network |
| RSESQ | (QC) Réseau de suivi des eaux souterraines du Québec |
| SWE | Snow Water Equivalent |
| SWMC | (ON) Surface Water Monitoring Centre |
| WFS | Web Feature Service |
| WMS | Web Map Service |
| WSA | Water Security Agency (Saskatchewan) |
| WSC | Water Survey of Canada |

### 3.3 Data-flow reference model

The reference model is a five-stage pipeline. Roles from Section 4 are applied at Stage 1; licensing
obligations from Section 10 attach at Stages 1 and 5.

```
        ┌──────────────────────────────────────────────────────────────────────┐
        │ STAGE 1 — UPSTREAM SOURCES                                             │
        │                                                                        │
        │  PRIMARY (provincial, where programmatic)      BACKUP / VALIDATION     │
        │  AB rivers • BC AQUARIUS(partial) • MB          ECCC/WSC national      │
        │  FloodInfo • ON KiWIS • QC Vigilance • NL       backbone:              │
        │  ADRS   [SK = scrape-only]                      Datamart (realtime)    │
        │                                                 HYDAT (validated)      │
        │  ECCC-PRIMARY jurisdictions (no prov. feed):    GeoMet OGC (meta+hist) │
        │  NB • NS • PE • NT • NU • YT  → Datamart         City Page • AQHI •    │
        │                                                 climate • RDPA         │
        │  ENRICHMENT: drainage, groundwater, flood,                             │
        │  snow, ice, weather, water-temp providers                              │
        └───────────────┬────────────────────────────────────────────────────┘
                        │ HTTP(S) pull (OGC API, bulk CSV, WFS/WMS, REST, ERDDAP)
                        ▼
        ┌──────────────────────────────────────────────────────────────────────┐
        │ STAGE 2 — INGESTION / PROBES  (harness; run_id=probes-20260916T090344Z)│
        │  Polite pull • descriptive UA • honour Retry-After • no cache-bypass   │
        └───────────────┬────────────────────────────────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────────────────────────────┐
        │ STAGE 3 — NORMALIZATION & QA/QC                                        │
        │  Unit/datum/CRS harmonization • flag mapping (LEVEL_SYMBOL /           │
        │  DISCHARGE_SYMBOL / Datamart QA 1–4) • provisional vs validated tag    │
        └───────────────┬────────────────────────────────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────────────────────────────┐
        │ STAGE 4 — STORAGE                                                      │
        │  Validated history (HYDAT backbone) + realtime cache (Datamart/prov.)  │
        │  + provenance/lineage metadata (source ID, licence, fetch time)        │
        └───────────────┬────────────────────────────────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────────────────────────────┐
        │ STAGE 5 — API / APPLICATION                                            │
        │  Attribution strings enforced • commercial/non-commercial gate         │
        │  • provisional badge preserved to the user                             │
        └──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data-Source Registry (Master Table)

The registry comprises **90 probes** — **86 sanctioned + 4 residual** — resolving to **40 distinct
Source IDs**, across **12 categories** with the following per-category probe counts (registry, measured
run `probes-20260916T090344Z`): aqi 2, current 20, stations 15, historical 19, drainage 6, groundwater
6, flood 6, precip 4, ice 3, snow 3, weather 4, watertemp 2 (sum = 90). The measured `coverage.csv`
covers the **86 sanctioned** probes, of which **80 were retrievable** (6 not retrievable; see Sections
8 and 14). A single Source ID such as `SRC-ECCC-DATAMART` expands to one probe per province/territory
(14 realtime jurisdictional pulls: AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT — 13 P/T — plus
the national context).

### 4.1 Master registry table (sanctioned sources)

Role legend: **P** = primary, **B** = backup/validation, **E** = enrichment. Status reflects the
2026-09-16 run.

| Source ID | Publisher | Role | Category(ies) | Status (2026-09-16) |
|-----------|-----------|------|---------------|---------------------|
| SRC-ECCC-DATAMART | ECCC / MSC (WSC) | B nationally; **P** for NB, NS, PE, NT, NU, YT (+ SK/AB/BC fallback) | current | Retrievable, all 13 P/T |
| SRC-ECCC-GEOMET | ECCC / MSC | B / E (station metadata + realtime + historical products) | current, stations, historical | Retrievable |
| SRC-ECCC-GEOMET-DAILY | ECCC / MSC | B (daily-mean depth history) | historical | Retrievable, all 13 P/T |
| SRC-HYDAT | ECCC / WSC | B (validated historical backbone) | historical | Retrievable |
| SRC-ECCC-CITYPAGE | ECCC / MSC | E (weather; commercial-safe weather fallback) | weather | Retrievable |
| SRC-ECCC-AQHI | ECCC / MSC | E (air quality) | aqi | Retrievable |
| SRC-ECCC-CLIMATE | ECCC / MSC | B / E (climate stations, daily/hourly/monthly, RDPA/CaPA) | stations, precip | Retrievable |
| SRC-ECCC-WATERPRED | ECCC / MSC (GeoMet) | B (water prediction) | flood | **Not retrievable — `ok_empty`** |
| SRC-BC-ASWS | BC (snow survey) | E (near-real-time SWE) | snow | Retrievable |
| SRC-BC-FWA | BC | E (watershed boundaries) | drainage | Retrievable |
| SRC-BC-RFC | BC River Forecast Centre | E (flood warnings) | flood | Retrievable |
| SRC-MB-FLOODINFO | Manitoba | **P (MB)** (level/flow/forecast/alert) | current | Retrievable |
| SRC-MB-HFC | Manitoba Hydrologic Forecast Centre | E (flood; HTML/PDF) | flood | Retrievable (no structured fields) |
| SRC-ON-KIWIS | Ontario SWMC | **P (ON)** (station list; KiWIS) | stations | Retrievable |
| SRC-ON-OIH | Ontario | E (integrated hydrology) | drainage | Retrievable |
| SRC-ON-PGMN | Ontario | E (groundwater; CKAN) | groundwater | Retrievable |
| SRC-ON-CO | Conservation Ontario | E (flood warnings; HTML/PDF) | flood | **Not retrievable — HTTP 404 (page moved)** |
| SRC-QC-VIGILANCE | Gouvernement du Québec | **P (QC)** (stations + flood; WFS/GeoJSON) | current, flood | Retrievable |
| SRC-QC-GRHQ | Gouvernement du Québec | E (hydro network) | drainage | Retrievable |
| SRC-QC-RSESQ | Gouvernement du Québec | E (groundwater; CKAN) | groundwater | Retrievable |
| SRC-NL-ADRS | Newfoundland & Labrador | **P (NL)** (per-station level/flow/WATER_TEMP CSV) | current | Retrievable |
| SRC-NHN | NRCan | E (National Hydro Network) | drainage | Retrievable |
| SRC-HYDROSHEDS | WWF / HydroSHEDS | E (HydroBASINS) | drainage | Retrievable |
| SRC-WSC-BASINS | ECCC / WSC | B / E (gauge drainage-basin polygons keyed to WSC #) | drainage | Retrievable |
| SRC-GIN | NRCan / GSC | E (groundwater WMS; 44 layers) | groundwater | Retrievable |
| SRC-STA-GW | GSC (SensorThings) | E (groundwater; national, ON, QC) | groundwater | **Not retrievable — DNS error ×3** |
| SRC-NRCAN-FLOOD | NRCan | E (FHIMP flood-mapping hub) | flood | Retrievable (no structured fields) |
| SRC-CANSWE | ECCC (via Zenodo) | E (national SWE metadata) | snow | Retrievable |
| SRC-CIS-ICE | Canadian Ice Service | E (ice-thickness archive page) | ice | Retrievable (no structured fields) |
| SRC-CRID | ECCC / NHP | E (Canadian River Ice Database; 196 sites) | ice | Retrievable — `ok_empty` |
| SRC-LAKEICE | ECCC | E (Lake Ice Database) | ice | Retrievable — `ok_empty` |
| SRC-RIVTEMP | RivTemp via DataStream | E (river water temperature) | watertemp | **Not retrievable — HTTP 401 (API key required)** |
| SRC-CIOOS | CIOOS Atlantic (ERDDAP) | E (coastal water temperature) | watertemp | Retrievable |
| SRC-MET-NORWAY | MET Norway | E (weather; commercial-safe fallback) | weather | Retrievable |
| SRC-OPEN-METEO | Open-Meteo | E (weather; full 27-field app contract) | weather | Retrievable |
| SRC-OPEN-METEO-AQI | Open-Meteo | E (air quality) | aqi | Retrievable |
| SRC-OPEN-METEO-ARCHIVE | Open-Meteo | E (ERA5 reanalysis) | historical | Retrievable |

### 4.2 Registry notes

- `SRC-ECCC-DATAMART` is simultaneously the **primary** feed for the six ECCC-primary jurisdictions
  (NB, NS, PE, NT, NU, YT) — those with no programmatic provincial river feed — and the **backup/
  validation** feed everywhere else. It is also the pragmatic programmatic primary for Alberta,
  British Columbia, and Saskatchewan whenever the provincial feed is scrape-only, undocumented, or
  intermittently refusing (Section 14).
- **Quebec exception:** ECCC Datamart carries only **15** QC real-time stations (measured), so QC's
  primary is `SRC-QC-VIGILANCE`. Datamart QC remains a thin cross-check only.
- The historical backbone is `SRC-HYDAT` (validated) plus `SRC-ECCC-GEOMET` / `SRC-ECCC-GEOMET-DAILY`
  (daily/monthly/annual products).

### 4.3 Residual sources (sanctioned = False; harness-only)

These four probes are **not** part of the sanctioned acquisition path and are exercised only by the
manual/overnight stress harness (`tests/stress_test.py`). They are retained in the registry for
completeness and for the Part 3 dated addendum.

| Source ID | Publisher | Nature | Licence / commercial | Measured status |
|-----------|-----------|--------|----------------------|-----------------|
| SRC-AB-RIVERS | Government of Alberta (rivers.alberta.ca) | Per-station JSON; **primary AB** if used, but scrape-class | GoA copyright; **commercial = NO** | Intermittent connection refusal (MEASURED); bad-path → 404 |
| SRC-SK-WSA | Water Security Agency (wsask.ca) | htmlwidget scrape; **primary SK** values are scrape-only | SK Crown copyright; **commercial = NO** | Scrape-only |
| SRC-BC-AQUARIUS | British Columbia | Undocumented AQUARIUS endpoint; **partial BC primary** | OGL-BC | Undocumented |
| (Open-Meteo rapid-burst probe) | Open-Meteo | "Too-fast" burst probe for knee-finding | CC-BY-4.0; free tier non-commercial | Smoke-validated; full run is user-launched |

---

## 5. Per-Source Datasheets

Each datasheet states publisher, role, endpoints and API version, formats and quirks, a field
dictionary (with units/datum/CRS where relevant), parameters/pagination, and caveats. Measured figures
carry the tag *(MEASURED)*; everything else is advertised.

### 5.1 SRC-ECCC-DATAMART — MSC Datamart hydrometric real-time bulk CSV

- **Publisher / role:** ECCC / MSC (Water Survey of Canada). Backup/validation nationally; **primary**
  for NB, NS, PE, NT, NU, YT; pragmatic primary for AB/BC/SK where provincial is unavailable.
- **Endpoints / API version:** MSC Datamart HTTPS file tree, `hydrometric/csv/<PROV>/` with `hourly/`
  and `daily/` bulk CSV bundles per province/territory. No API versioning; served as a static file
  tree. [1]
- **Formats / quirks:** Comma-separated bulk CSV, one bundle per P/T. Large provinces are slow to pull:
  AB latency **7,950 ms** and ON **7,238 ms** *(MEASURED)* versus PE **534 ms** and QC **505 ms**.
  `hourly` bundles carry roughly the last ~2 days; `daily` bundles roughly the last ~30 days
  (Section 7). No pagination — the whole bundle is retrieved.
- **Field dictionary (10 fields *(MEASURED)*):** station ID (WSC number), date/time (UTC), water level
  (m; datum is the station's gauge datum, geodetic where established), discharge (m³/s), and per-value
  QA/QC grade and symbol fields (Datamart QA flags 1–4; Section 8).
- **Parameters:** Selection is by province/territory directory and by hourly/daily bundle. No query
  parameters.
- **Coverage *(MEASURED)*:** realtime station_count per P/T — AB 409, BC 436, MB 250, NB 51, NL 97,
  NS 39, NT 100, NU 24, ON 523, PE 9, QC 15, SK 150, YT 72 (≈ **2,160** stations nationally);
  record_count in the sample summed to ≈ **1,280,040** rows.
- **Caveats:** Values are **provisional** (Section 8). QC carries only 15 stations (the exception).
  Retrieval MUST respect the ECCC acceptable-use ceiling (~1 req/s / ~86,400 req/day before contacting
  MSC) and MUST NOT send cache-bypass headers (Section 10).

### 5.2 SRC-ECCC-GEOMET — GeoMet OGC API (metadata + realtime + historical products)

- **Publisher / role:** ECCC / MSC. Backup/validation and enrichment; the OGC API front door for
  station metadata and the daily/monthly/annual historical products, plus a realtime hydrometric
  collection.
- **Endpoints / API version:** GeoMet OGC API — Features / EDR (`/collections/...`, OGC API - Features
  Part 1). Collections used include `hydrometric-stations`, `hydrometric-realtime`,
  `hydrometric-daily-mean`, `hydrometric-monthly-mean`, `hydrometric-annual-statistics`, and
  `hydrometric-annual-peaks`. [2][45]
- **Formats / quirks:** GeoJSON feature responses; standard OGC bbox/datetime query. Realtime national
  sample returned 13 fields, 10 records, 1 station *(MEASURED)*; latency 259 ms. Reference station
  `05BB001` (Bow River at Banff) returned: annual-peaks earliest **1923**, span **103 y**;
  annual-statistics earliest **1909**, span **117 y**; daily-mean earliest **1989**; monthly-mean
  earliest **1909** *(MEASURED)*.
- **Field dictionary:** station identifier, geometry (lon/lat, **CRS EPSG:4326 / WGS84**), datetime,
  and per-product measures (level m, discharge m³/s, annual peak/statistic values). Stations catalogue
  carries 14 fields *(MEASURED)*.
- **Parameters / pagination:** OGC API - Features `bbox`, `datetime`, `limit`, and `offset`/`startindex`
  paging. EDR position/area queries where supported.
- **Caveats:** GeoMet is the metadata and historical **product** path; it is not a substitute for HYDAT
  depth of validation. Same ECCC acceptable-use limits as 5.1.

### 5.3 SRC-ECCC-GEOMET-DAILY — daily-mean depth (per province/territory)

- **Publisher / role:** ECCC / MSC. Backup (historical daily-mean depth by jurisdiction).
- **Endpoints / API version:** GeoMet OGC API daily-mean collection, queried per P/T. [2]
- **Formats / quirks:** GeoJSON; 12 fields *(MEASURED)*; fast (latencies 72–81 ms typical; NU probe
  672 ms *(MEASURED)*).
- **Coverage — earliest year by P/T *(MEASURED)*:** AB 1908, BC 1960, MB 1957, NB 1951, NL 1999,
  NS 1964, NT 2017, NU 1970, ON 1972, PE 1919, QC 1967, SK 1911, YT 1950.
- **Field dictionary:** station ID, date, daily-mean level/discharge, geometry (WGS84).
- **Caveats:** span-years values in the sample reflect the sampled window, not the full period of
  record; use HYDAT for full validated series.

### 5.4 SRC-HYDAT — National Water Data Archive (validated historical backbone)

- **Publisher / role:** ECCC / WSC. Backup/validation — the deepest validated archive; the historical
  backbone of the standard.
- **Endpoints / API version:** HYDAT is distributed as a downloadable SQLite database (National Water
  Data Archive); refreshed quarterly. [3]
- **Formats / quirks:** Relational SQLite; **106 fields** across its tables *(MEASURED)*. It is a bulk
  archive, not a streaming API — ingestion is a periodic download-and-load.
- **Coverage *(MEASURED)*:** **1,779,871** records, **6,478** stations, earliest year **1860**, span
  **167 years**; fetch/load probe latency 385 ms.
- **Field dictionary (selected):** STATION_NUMBER, STATION_NAME, PROV_TERR_STATE_LOC, LATITUDE/
  LONGITUDE (WGS84), DRAINAGE_AREA, per-day level/flow with `LEVEL_SYMBOL` / `DISCHARGE_SYMBOL` grade
  codes (Section 8), plus annual statistics/peaks tables.
- **Caveats:** HYDAT is **validated** (authoritative for history) but **lags** real time by up to a
  quarter (Section 7). It MUST be the source of truth when a value conflicts with provisional Datamart.

### 5.5 SRC-ECCC-CITYPAGE — City Page Weather

- **Publisher / role:** ECCC / MSC. Enrichment (weather); the commercial-safe weather fallback for
  Posture B.
- **Endpoints / API version:** MSC City Page Weather XML — per-city XML documents plus a site
  catalogue CSV. [4]
- **Formats / quirks:** Per-city XML (Calgary probe: 20 fields, 11 records, latency **63 ms**
  *(MEASURED)* — the fastest source in the run); national site catalogue CSV lists **856** sites
  *(MEASURED)*.
- **Field dictionary:** current conditions (temperature °C, wind, humidity %, pressure kPa), short-term
  forecast, warnings; catalogue holds site code, name, lat/lon, province.
- **Caveats:** City-based, not station-based; join to stations by geography. Commercial = YES (unlike
  Open-Meteo free tier), which makes it the recommended commercial weather substitute.

### 5.6 SRC-ECCC-AQHI — Air Quality Health Index (GeoMet OGC API)

- **Publisher / role:** ECCC / MSC. Enrichment (air quality).
- **Endpoints / API version:** GeoMet OGC API AQHI observations collection. [5][2]
- **Formats / quirks:** GeoJSON; 14 fields, **6,996** records, **10** stations, latency 397 ms
  *(MEASURED)*.
- **Field dictionary:** station/location, datetime, AQHI value (index), geometry (WGS84).
- **Caveats:** Observation set is station-sparse relative to weather; pair with Open-Meteo AQI for
  spatial fill in non-commercial mode only.

### 5.7 SRC-ECCC-CLIMATE — climate stations, daily/hourly/monthly, RDPA/CaPA

- **Publisher / role:** ECCC / MSC. Backup/enrichment (climate + precipitation + station catalogue).
- **Endpoints / API version:** GeoMet-Climate OGC API collections: `climate-stations`,
  `climate-daily`, `climate-hourly`, `climate-monthly`, and RDPA/CaPA 10 km 6 h analysis metadata. [6]
- **Formats / quirks / coverage *(MEASURED)*:** `climate-stations` 33 fields, **8,435** stations,
  earliest 1965; `climate-daily` 34 fields, **184,672,664** records, earliest **1876**, span 138 y
  (includes precip + snow_on_ground); `climate-hourly` 40 fields, **277,058,947** records, earliest
  1972; `climate-monthly` 34 fields, **1,881,824** records, earliest 1990; RDPA/CaPA 10 km 6 h returns
  6 metadata fields.
- **Field dictionary:** station ID, datetime, air temperature (°C), total precipitation (mm),
  snow_on_ground (cm), plus flags; geometry WGS84.
- **Caveats:** Very large collections; page and filter tightly; never bulk-scan.

### 5.8 SRC-AB-RIVERS — Alberta River Basins (rivers.alberta.ca)

- **Publisher / role:** Government of Alberta. Would be **primary (AB)**, but is a residual/scrape-class
  per-station JSON source and is **commercially blocked**.
- **Endpoints / API version:** Per-station JSON on rivers.alberta.ca; no documented public API version.
- **Formats / quirks:** Per-station JSON; **intermittent connection refusal** observed *(MEASURED)*;
  bad path returns 404. Behind an "authorized users only" gate.
- **Field dictionary:** station, level, flow, timestamp (as published per station).
- **Caveats:** GoA copyright; **commercial = NO** without written permission; non-commercial reuse OK
  with attribution "Government of Alberta". Because of the intermittency and licence, ECCC Datamart is
  the sanctioned AB path. See Sections 10 and 14.

### 5.9 SRC-MB-FLOODINFO — Manitoba FloodInfo (AGOL CSV)

- **Publisher / role:** Manitoba. **Primary (MB)**.
- **Endpoints / API version:** ArcGIS Online (AGOL) hosted CSV feed exposing level/flow/forecast/alert.
  [13]
- **Formats / quirks:** CSV; **30 fields**, **248** records, latency 231 ms *(MEASURED)*.
- **Field dictionary:** station, water level (m), flow (m³/s), forecast values, alert/threshold status,
  timestamp; geometry where present in WGS84.
- **Caveats:** OpenMB licence; commercial = YES with the OpenMB attribution string (Section 10). The
  companion `SRC-MB-HFC` (Hydrologic Forecast Centre) is HTML/PDF only (0 structured fields
  *(MEASURED)*), licence unspecified — treat as human-readable context, not a machine feed.

### 5.10 SRC-ON-KIWIS — Ontario SWMC KiWIS

- **Publisher / role:** Ontario Surface Water Monitoring Centre. **Primary (ON)** for station listing.
- **Endpoints / API version:** KiWIS (Kisters WISKI) REST — `getStationList` and related requests. [19]
- **Formats / quirks:** KiWIS JSON/CSV; `getStationList` returned 5 fields, **4,436** stations, latency
  **2,004 ms** *(MEASURED)*.
- **Field dictionary:** station_no, station_name, station latitude/longitude (WGS84), station_id.
- **Parameters / pagination:** KiWIS `request=getStationList`, `format`, `returnfields`; KiWIS supports
  its own paging/return-field selection.
- **Caveats:** The probe measured the station list; time-series values require follow-on
  `getTimeseriesValues` requests. OGL-Ontario; commercial = YES.

### 5.11 SRC-QC-VIGILANCE — Quebec Vigilance (WFS / GeoJSON)

- **Publisher / role:** Gouvernement du Québec. **Primary (QC)** — the sole primary for QC given the
  ECCC exception.
- **Endpoints / API version:** Vigilance WFS returning station and flood GeoJSON. [24]
- **Formats / quirks:** GeoJSON; stations probe 13 fields, **50** records, **50** stations, latency
  505 ms *(MEASURED)*; flood WFS returned 13 fields, 1 record *(MEASURED)*.
- **Field dictionary:** station ID, name, level/flow, vigilance/alert status, geometry (WGS84).
- **Caveats:** CC-BY 4.0 (Québec); attribute "Gouvernement du Québec". Because ECCC carries only 15 QC
  realtime stations, Vigilance is authoritative for QC realtime.

### 5.12 SRC-NL-ADRS — Newfoundland & Labrador per-station CSV

- **Publisher / role:** Newfoundland and Labrador. **Primary (NL)**.
- **Endpoints / API version:** ADRS per-station CSV endpoints. [28]
- **Formats / quirks:** Per-station CSV carrying level, flow, and `WATER_TEMP`; probe returned 1 field
  schema, **2,005** records, 1 station, latency 599 ms *(MEASURED)*.
- **Field dictionary:** timestamp, water level (m), flow (m³/s), WATER_TEMP (°C).
- **Caveats:** OGL-NL; commercial = YES. Per-station fetch pattern — iterate the station list rather
  than a single bulk pull.

### 5.13 SRC-CANSWE — national Snow Water Equivalent (Zenodo)

- **Publisher / role:** ECCC dataset published via Zenodo. Enrichment (snow).
- **Endpoints / API version:** Zenodo record (dataset + metadata). [35]
- **Formats / quirks:** Dataset with 8 metadata fields, 4 records in the metadata probe, earliest
  **1928**, span 98 y, latency **4,604 ms** *(MEASURED)* (archive fetch is slow).
- **Field dictionary:** station, date, SWE (mm), snow depth (cm), source network.
- **Caveats:** Research dataset cadence (periodic version releases), not real time. Pair with
  `SRC-BC-ASWS` (122 fields, **8,409** records, 121 stations, latency 816 ms *(MEASURED)*) for BC
  near-real-time SWE.

### 5.14 SRC-CRID — Canadian River Ice Database

- **Publisher / role:** ECCC / National Hydrometric Program. Enrichment (ice).
- **Endpoints / API version:** CRID distribution covering **196** NHP sites. [37]
- **Formats / quirks:** Probe returned `ok_empty` — reachable but the light sample produced no rows/no
  file link; 196 stations advertised, earliest **1894**, span **122 y**, latency 595 ms *(MEASURED)*.
- **Field dictionary:** site, date, ice observation/thickness class (per CRID schema).
- **Caveats:** Requires a deeper query to materialize rows; treat current status as retrievable but
  empty on the light path.

### 5.15 SRC-WSC-BASINS — WSC gauge drainage-basin polygons

- **Publisher / role:** ECCC / WSC. Backup/enrichment (drainage geometry keyed to WSC station number).
- **Endpoints / API version:** WSC drainage-basin polygon distribution keyed to WSC station #. [31]
- **Formats / quirks:** Polygon features; probe returned 1 field, 1 record, latency 360 ms *(MEASURED)*.
- **Field dictionary:** WSC station number (join key), basin polygon geometry (WGS84 / as published).
- **Caveats:** Join strictly on WSC station number; polygon set is not exhaustive for every gauge.

### 5.16 SRC-STA-GW — GSC SensorThings groundwater (national / ON / QC)

- **Publisher / role:** Geological Survey of Canada (NRCan). Enrichment (groundwater).
- **Endpoints / API version:** OGC SensorThings API, host `mon.geosciences.ca`. [33]
- **Formats / quirks:** **Not retrievable — DNS error on all three probes** (national, ON, QC)
  *(MEASURED)*: the officially catalogued federal groundwater SensorThings host did not resolve during
  testing. This is a genuine availability/reliability finding (Section 14), not a client fault.
- **Field dictionary:** (SensorThings entity model — Things/Locations/Datastreams/Observations) — not
  materialized in this run.
- **Caveats:** Use `SRC-GIN` (Groundwater Information Network WMS; **44** layers, latency 797 ms
  *(MEASURED)*) as the working federal groundwater alternative until the host resolves.

### 5.17 SRC-RIVTEMP — RivTemp via DataStream (OData v4)

- **Publisher / role:** RivTemp, delivered through DataStream. Enrichment (river water temperature).
- **Endpoints / API version:** DataStream **OData v4** API. [39]
- **Formats / quirks:** **Not retrievable — HTTP 401 unauthorized** *(MEASURED)*: an **API key is
  required** (`x-api-key`), documented, ~2 req/s. This is an auth prerequisite, not an endpoint failure.
- **Field dictionary:** station, datetime, water temperature (°C) per DataStream dataset schema.
- **Caveats:** Commercial = CONDITIONAL (per-dataset OGC/CC-BY/custom terms). Obtain and store the API
  key in the secrets path (Section 13) before enabling.

### 5.18 SRC-CIOOS — CIOOS Atlantic ERDDAP catalogue

- **Publisher / role:** CIOOS Atlantic. Enrichment (coastal water temperature).
- **Endpoints / API version:** ERDDAP catalogue / tabledap. [40]
- **Formats / quirks:** ERDDAP responses (CSV/JSON); probe returned 16 fields, 10 records, latency
  164 ms *(MEASURED)*.
- **Field dictionary:** platform/station, time, sea/water temperature (°C), lat/lon (WGS84), depth.
- **Caveats:** Coastal (marine) water temperature, not river — use for estuary/coastal context only.
  Licence is per-dataset (CC-BY / OGL-Canada / CC0).

### 5.19 SRC-MET-NORWAY — MET Norway Locationforecast

- **Publisher / role:** MET Norway. Enrichment (weather); a commercial-safe weather fallback.
- **Endpoints / API version:** Locationforecast **compact** product (MET Norway API). [41]
- **Formats / quirks:** JSON; 11 fields, **91** records, latency 513 ms *(MEASURED)*. A **descriptive
  User-Agent is required** by MET Norway terms.
- **Field dictionary:** time, air_temperature (°C), wind_speed (m/s), precipitation (mm), pressure
  (hPa), humidity (%).
- **Caveats:** CC-BY 4.0 / NLOD 2.0; commercial = YES with "Data from MET Norway" attribution.

### 5.20 SRC-OPEN-METEO — Open-Meteo forecast (full 27-field app weather contract)

- **Publisher / role:** Open-Meteo. Enrichment (weather); supplies the complete 27-field WaterPulse
  weather contract.
- **Endpoints / API version:** Open-Meteo forecast API. [42]
- **Formats / quirks:** JSON; **27 fields** = the full app weather contract, 7 records, 1 station,
  latency 380 ms *(MEASURED)*. Free tier limits: **600/min, 5,000/hr, 10,000/day**.
- **Field dictionary:** hourly/daily temperature (°C), precipitation (mm), wind (m/s), humidity (%),
  cloud cover (%), and the remaining app contract fields.
- **Caveats:** CC-BY 4.0 but the **free tier is NON-COMMERCIAL only**. For a commercial tier this
  source SHALL be replaced by a paid Open-Meteo plan or by `SRC-ECCC-CITYPAGE` / `SRC-MET-NORWAY`.
  Companion probes: `SRC-OPEN-METEO-AQI` (5 fields, us_aqi + pm2_5/pm10, latency 833 ms) and
  `SRC-OPEN-METEO-ARCHIVE` (ERA5; 3 fields, 31 records, earliest **1940**, latency 688 ms), same
  licence/limits.

### 5.21 Consolidated datasheet — remaining sources

| Source ID | Publisher | Role/category | Endpoint / format | Key measured facts | Notes |
|-----------|-----------|---------------|-------------------|--------------------|-------|
| SRC-BC-FWA | BC | E / drainage | Freshwater Atlas boundaries | 5 fields, 8 recs, 485 ms | Watershed polygons; OGL-BC-2.0 |
| SRC-BC-RFC | BC River Forecast Centre | E / flood | ArcGIS warnings | 10 fields, 5 recs, 523 ms | OGL-BC |
| SRC-BC-ASWS | BC | E / snow | Wide CSV (SWE) | 122 fields, 8,409 recs, 121 stn, 816 ms | Near-real-time SWE |
| SRC-ON-OIH | Ontario | E / drainage | Integrated Hydrology | 2 fields, 7 recs, 392 ms | OGL-Ontario-1.0 |
| SRC-ON-PGMN | Ontario | E / groundwater | CKAN | 44 fields, 7 recs, 733 ms | OGL-Ontario |
| SRC-ON-CO | Conservation Ontario | E / flood | HTML/PDF | **HTTP 404 (page moved)** | No API; human-readable only |
| SRC-QC-GRHQ | Québec | E / drainage | Hydro network | 6 fields, 10 recs, 390 ms | CC-BY-4.0 |
| SRC-QC-RSESQ | Québec | E / groundwater | CKAN | 53 fields, 20 recs, 430 ms | CC-BY-4.0 |
| SRC-NHN | NRCan | E / drainage | National Hydro Network | 7 fields, 15 recs, 409 ms | OGL-Canada-2.0 |
| SRC-HYDROSHEDS | WWF/HydroSHEDS | E / drainage | HydroBASINS | 13 fields, 200 ms | HydroSHEDS Licence |
| SRC-GIN | NRCan/GSC | E / groundwater | WMS GetCapabilities | **44 layers**, 797 ms | Working GW alternative to SensorThings |
| SRC-NRCAN-FLOOD | NRCan | E / flood | FHIMP hub | 0 fields, 187 ms | Map hub, not a value feed |
| SRC-MB-HFC | Manitoba | E / flood | HTML/PDF | 0 fields, 289 ms | Licence unspecified; context only |
| SRC-CIS-ICE | Canadian Ice Service | E / ice | Archive page | 0 fields, 3,167 ms | Slow; archive page |
| SRC-LAKEICE | ECCC | E / ice | Lake Ice DB | `ok_empty`, 532 ms | Needs deeper query |
| SRC-ECCC-WATERPRED | ECCC/GeoMet | B / flood | Water-prediction collections | **`ok_empty`**, 350 ms | Reachable, no rows on light sample |
| SRC-OPEN-METEO-AQI | Open-Meteo | E / aqi | Air Quality API | 5 fields, 833 ms | Free tier non-commercial |
| SRC-OPEN-METEO-ARCHIVE | Open-Meteo | E / historical | ERA5 archive | 3 fields, 31 recs, earliest 1940, 688 ms | Free tier non-commercial |

---

## 6. Spatial & Temporal Coverage

### 6.1 Real-time hydrometric coverage per province/territory (Datamart, MEASURED)

| P/T | Realtime stations | Sample records | Latency (ms) | Notes |
|-----|-------------------|----------------|--------------|-------|
| AB | 409 | 236,259 | 7,950 | Largest AB pull; slow |
| BC | 436 | 247,941 | 1,468 | Largest station count |
| MB | 250 | 146,821 | 1,096 | Primary = FloodInfo |
| NB | 51 | 31,767 | 643 | ECCC-primary |
| NL | 97 | 60,635 | 733 | Primary = ADRS |
| NS | 39 | 23,782 | 580 | ECCC-primary |
| NT | 100 | 56,924 | 837 | ECCC-primary |
| NU | 24 | 14,006 | 1,599 | ECCC-primary; sparsest |
| ON | 523 | 317,748 | 7,238 | Most stations & records; slow |
| PE | 9 | 5,571 | 534 | Smallest network |
| QC | 15 | 9,191 | 505 | **Exception** — primary = Vigilance |
| SK | 150 | 88,617 | 2,584 | Values scrape-only provincially |
| YT | 72 | 40,778 | 784 | ECCC-primary |
| **Total** | **≈ 2,160** | **≈ 1,280,040** | — | MEASURED |

QC's 15-station Datamart footprint is the quantitative basis for the Quebec exception: the province's
authoritative realtime signal is carried by `SRC-QC-VIGILANCE` (50 stations MEASURED), not by ECCC.

### 6.2 Station-catalogue coverage (GeoMet hydrometric-stations, MEASURED)

The GeoMet stations catalogue (active + historical/discontinued) is far larger than the realtime
footprint: AB 1,104, BC 2,324, MB 659, NB 144, NL 230, NS 144, NT 245, NU 109, ON 1,119, PE 43,
QC 1,001, SK 748, YT 114 — **≈ 7,984** stations nationally. The `SRC-ECCC-CLIMATE` catalogue adds
**8,435** climate stations; `SRC-ON-KIWIS` lists **4,436** Ontario stations.

### 6.3 Temporal (historical) coverage, MEASURED

- **HYDAT backbone:** **6,478** stations, **1,779,871** records, earliest **1860**, span **167 years** —
  the deepest validated series in the registry.
- **GeoMet reference station 05BB001:** annual-statistics from **1909** (span 117 y); annual-peaks from
  **1923** (span 103 y); monthly-mean from 1909.
- **GeoMet-daily depth, earliest year by P/T:** AB 1908, SK 1911, PE 1919, YT 1950, NB 1951, MB 1957,
  BC 1960, NS 1964, QC 1967, NU 1970, ON 1972, NL 1999, NT 2017.
- **Climate:** climate-daily from **1876** (184.7 M records), climate-hourly from 1972 (277.1 M
  records), climate-monthly from 1990.
- **Reanalysis / other:** Open-Meteo ERA5 archive from **1940**; CanSWE from **1928**; CRID sites
  advertised from **1894** (span 122 y).

### 6.4 Coverage gaps

- **Quebec realtime via ECCC** is limited to 15 stations by design (Section 6.1).
- **Federal groundwater (SensorThings)** coverage was unrealizable in this run (DNS; Section 14); GIN
  (44 layers) is the standing substitute.
- **Ice databases (CRID, LakeIce)** returned `ok_empty` on the light path; realized coverage requires a
  deeper query.

---

## 7. Cadence, Latency & Update Frequency

### 7.1 Publisher update cadence (advertised, except where MEASURED)

| Source | Cadence | Window / freshness |
|--------|---------|--------------------|
| Datamart `hourly` bundles | Hourly | Rolling last ~2 days |
| Datamart `daily` bundles | Daily | Rolling last ~30 days |
| GeoMet realtime | Sub-daily | Near real time |
| HYDAT | **Quarterly** | Validated archive; lags real time up to one quarter |
| GeoMet daily/monthly/annual products | Batch | Aligned to WSC processing |
| ECCC climate (daily/hourly/monthly) | Sub-daily to monthly | Per product |
| RDPA/CaPA | 6-hourly, 10 km | Analysis product |
| AQHI | Hourly | Observations |
| City Page weather | Sub-hourly | Current + forecast |
| MET Norway / Open-Meteo | Hourly/daily | Forecast |
| Provincial feeds (MB/ON/QC/NL/BC) | Sub-daily | Per provincial cadence |
| CanSWE / CRID / LakeIce | Periodic release | Research datasets |

### 7.2 Measured latencies (run probes-20260916T090344Z)

- **Whole run:** 80/86 sanctioned probes retrievable in **186.7 s**.
- **Fastest:** City Page Calgary XML **63 ms**; GeoMet-daily depth 72–81 ms; CIOOS 164 ms; NRCan flood
  187 ms; HydroSHEDS 200 ms.
- **Slowest:** Datamart AB **7,950 ms** and ON **7,238 ms** (large bundles); CIS ice archive 3,167 ms;
  CanSWE (Zenodo) 4,604 ms; SK Datamart 2,584 ms; ON KiWIS 2,004 ms.
- **Implication:** Ingestion scheduling SHOULD budget for multi-second pulls on AB/ON Datamart and on
  the archive/Zenodo endpoints, and SHOULD stagger them to stay well under the ECCC ~1 req/s ceiling
  (Section 10).

### 7.3 Freshness contract

Because Datamart is provisional and HYDAT is quarterly-validated, the application SHOULD present
realtime values with a "provisional" indicator and SHOULD reconcile against HYDAT on each quarterly
HYDAT refresh, replacing provisional history with validated history where they overlap (Sections 8–9).

---

## 8. Data Quality, QA/QC & Provisional Status

### 8.1 ECCC grade/symbol semantics

- **HYDAT `LEVEL_SYMBOL` / `DISCHARGE_SYMBOL`:** per-value qualifier codes in the validated archive
  (e.g., ice-affected, estimated, dry) that the application SHALL preserve and surface rather than
  silently drop.
- **Datamart QA/QC flags (grades 1–4):** each Datamart value carries a provisional QA grade on a 1–4
  scale. These are **provisional** grades assigned before HYDAT validation.

### 8.2 Validated vs provisional

| Attribute | Datamart (realtime) | HYDAT (archive) |
|-----------|---------------------|-----------------|
| Status | **Provisional** | **Validated** |
| Latency | Minutes–hours | Up to one quarter |
| Grading | QA flags 1–4 | LEVEL_SYMBOL / DISCHARGE_SYMBOL |
| Authority on conflict | Lower | **Higher (source of truth)** |

Per conformance clause C-6, where both a provisional and a validated value exist for the same
station-time, the validated value SHALL prevail and the provisional value SHALL be visibly marked as
provisional until reconciled.

### 8.3 Retrievability quality of this run

Of 86 sanctioned probes, **80 were retrievable**. Six were not, and three additional probes returned
`ok_empty`:

| Outcome | Source(s) | Interpretation |
|---------|-----------|----------------|
| DNS error ×3 | SRC-STA-GW (national, ON, QC) | Catalogued federal GW SensorThings host `mon.geosciences.ca` did not resolve — real availability finding; use GIN |
| HTTP 401 | SRC-RIVTEMP | API key required (documented) — not an endpoint failure |
| HTTP 404 | SRC-ON-CO | Conservation Ontario page moved (HTML only, no API) |
| `ok_empty` | SRC-ECCC-WATERPRED (also non-retrievable), SRC-CRID, SRC-LAKEICE | Endpoint reachable; light sample returned no rows/file link — needs a deeper query |

These outcomes are recorded, not hidden; each carries a mitigation (Sections 14 and 17).

---

## 9. Provenance, Lineage & Versioning

- **Per-datum provenance.** Every stored value SHALL retain: Source ID, publisher, licence identifier,
  fetch timestamp (UTC), upstream endpoint, and (where present) the upstream QA grade/symbol.
- **Run provenance.** Ingestion runs SHALL be identified by a `run_id` of the form
  `probes-<UTC timestamp>` (this Part's evidence base is `probes-20260916T090344Z`), enabling any
  figure in a report to be traced to a specific run and its `coverage.csv`.
- **Lineage.** The lineage of a displayed river value is: upstream publisher → Stage-2 probe → Stage-3
  normalization (unit/datum/CRS + flag mapping) → Stage-4 storage (validated backbone vs realtime
  cache) → Stage-5 API. Reconciliation from provisional to validated (Section 8.2) SHALL be recorded as
  a lineage event, not an in-place silent overwrite.
- **Versioning.** HYDAT is versioned by its quarterly release; GeoMet/OGC collections are versioned by
  the API and collection identity; Datamart bundles are versioned implicitly by their rolling window.
  The registry (Section 4) is versioned with this standard (v1.0).

---

## 10. Usage Rights, Licensing & Monetization (NORMATIVE)

This section is **normative**. It states, for every source, the licence, SPDX identifier, commercial
disposition, redistribution posture, attribution string, technical limits, and citation, and then the
composite most-restrictive analysis for a commercial tier. **No source is cut.**

### 10.1 Licence & commercial matrix (Table 10-A)

| Source ID | Publisher | Licence + version | SPDX | Commercial? | Monetization verdict |
|-----------|-----------|-------------------|------|-------------|----------------------|
| SRC-ECCC-DATAMART | ECCC/MSC | OGL-Canada 2.0 / ECCC End-use v2.1.1 | OGL-Canada-2.0 (custom) | **YES** | OK with attribution + acceptable-use compliance |
| SRC-ECCC-GEOMET | ECCC/MSC | OGL-Canada 2.0 / ECCC End-use v2.1.1 | OGL-Canada-2.0 | **YES** | OK |
| SRC-ECCC-GEOMET-DAILY | ECCC/MSC | OGL-Canada 2.0 | OGL-Canada-2.0 | **YES** | OK |
| SRC-HYDAT | ECCC/WSC | OGL-Canada 2.0 / ECCC End-use v2.1.1 | OGL-Canada-2.0 | **YES** | OK |
| SRC-ECCC-CITYPAGE | ECCC/MSC | OGL-Canada 2.0 / ECCC End-use v2.1.1 | OGL-Canada-2.0 | **YES** | OK — recommended commercial weather substitute |
| SRC-ECCC-AQHI | ECCC/MSC | OGL-Canada / MSC End-use v2.1.1 | OGL-Canada-2.0 | **YES** | OK |
| SRC-ECCC-CLIMATE | ECCC/MSC | OGL-Canada 2.0 | OGL-Canada-2.0 | **YES** | OK |
| SRC-ECCC-WATERPRED | ECCC/MSC | OGL-Canada | OGL-Canada-2.0 | **YES** | OK (once rows materialize) |
| SRC-NHN | NRCan | OGL-Canada 2.0 | OGL-Canada-2.0 | **YES** | OK |
| SRC-WSC-BASINS | ECCC/WSC | OGL-Canada 2.0 | OGL-Canada-2.0 | **YES** | OK |
| SRC-GIN | NRCan/GSC | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-STA-GW | GSC | OGL-Canada | OGL-Canada-2.0 | **YES** | OK (blocked by DNS, not licence) |
| SRC-NRCAN-FLOOD | NRCan | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-CANSWE | ECCC | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-CIS-ICE | Canadian Ice Service | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-CRID | ECCC/NHP | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-LAKEICE | ECCC | OGL-Canada | OGL-Canada-2.0 | **YES** | OK |
| SRC-AB-RIVERS | Government of Alberta | GoA copyright | none | **NO** | **BLOCKER** — written permission required; non-commercial OK |
| SRC-SK-WSA | Water Security Agency (SK) | SK Crown copyright | none | **NO** | **BLOCKER** — written permission required; scrape-only values |
| SRC-MB-FLOODINFO | Manitoba | OpenMB Information & Data Use Licence | none (custom) | **YES** | OK with OpenMB attribution |
| SRC-MB-HFC | Manitoba | Unspecified | none | **UNKNOWN** | Treat as context only until clarified |
| SRC-BC-ASWS | BC | OGL – British Columbia 2.0 | OGL-BC-2.0 (custom) | **YES** | OK |
| SRC-BC-FWA | BC | OGL – British Columbia 2.0 | OGL-BC-2.0 | **YES** | OK |
| SRC-BC-RFC | BC | OGL – British Columbia | OGL-BC-2.0 | **YES** | OK |
| SRC-BC-AQUARIUS | BC | OGL – British Columbia | OGL-BC-2.0 | **YES** | OK (undocumented endpoint) |
| SRC-ON-KIWIS | Ontario | OGL – Ontario | OGL-Ontario (custom) | **YES** | OK |
| SRC-ON-OIH | Ontario | OGL – Ontario 1.0 | OGL-Ontario | **YES** | OK |
| SRC-ON-PGMN | Ontario | OGL – Ontario | OGL-Ontario | **YES** | OK |
| SRC-ON-CO | Conservation Ontario | Unspecified | none | **UNKNOWN** | Context only; page moved |
| SRC-QC-VIGILANCE | Gouvernement du Québec | CC-BY 4.0 (Québec) | CC-BY-4.0 | **YES** | OK with QC attribution |
| SRC-QC-GRHQ | Gouvernement du Québec | CC-BY 4.0 | CC-BY-4.0 | **YES** | OK |
| SRC-QC-RSESQ | Gouvernement du Québec | CC-BY 4.0 | CC-BY-4.0 | **YES** | OK |
| SRC-NL-ADRS | Newfoundland & Labrador | OGL – Newfoundland and Labrador | OGL-NL (custom) | **YES** | OK |
| SRC-HYDROSHEDS | WWF / HydroSHEDS | HydroSHEDS Licence | none (custom) | **YES** | OK with HydroSHEDS attribution |
| SRC-RIVTEMP | RivTemp via DataStream | Per-dataset (OGC / CC-BY / custom) | varies | **CONDITIONAL** | Depends on dataset; API key required |
| SRC-CIOOS | CIOOS Atlantic | CC-BY 4.0 / OGL-Canada / CC0 (per dataset) | CC-BY-4.0 / OGL-Canada-2.0 / CC0-1.0 | **YES** | OK |
| SRC-MET-NORWAY | MET Norway | CC-BY 4.0 / NLOD 2.0 | CC-BY-4.0 | **YES** | OK with MET attribution + descriptive UA |
| SRC-OPEN-METEO | Open-Meteo | CC-BY 4.0 (free tier **non-commercial**) | CC-BY-4.0 | **NO (free tier)** | **BLOCKER (free tier)** — paid plan or substitute |
| SRC-OPEN-METEO-AQI | Open-Meteo | CC-BY 4.0 (free tier non-commercial) | CC-BY-4.0 | **NO (free tier)** | Same as above |
| SRC-OPEN-METEO-ARCHIVE | Open-Meteo | CC-BY 4.0 (free tier non-commercial) | CC-BY-4.0 | **NO (free tier)** | Same as above |

### 10.2 Attribution, redistribution, limits & citation (Table 10-B)

Keyed by Source ID to Table 10-A. Redistribution is permitted for all OGL/CC-BY/OpenMB/HydroSHEDS
sources with attribution; blocked/conditional sources are flagged.

| Source ID | Attribution string | Redistribution | Technical limits | Citation ref |
|-----------|--------------------|----------------|------------------|--------------|
| SRC-ECCC-DATAMART | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | Contact MSC ≥ ~86,400 req/day (~1 req/s); **no cache-bypass headers**; no bulk WMS-tile retrieval | [1][8][9] |
| SRC-ECCC-GEOMET / -DAILY | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | Same ECCC acceptable-use ceiling; page/limit queries | [2][8][9] |
| SRC-HYDAT | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | Bulk SQLite; refresh quarterly | [3][8] |
| SRC-ECCC-CITYPAGE | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | ECCC acceptable-use | [4][8][9] |
| SRC-ECCC-AQHI | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | ECCC acceptable-use | [5][8] |
| SRC-ECCC-CLIMATE | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | Very large collections — tight paging | [6][8] |
| SRC-ECCC-WATERPRED | "Data Source: Environment and Climate Change Canada" | Permitted w/ attribution | ECCC acceptable-use | [7][8] |
| SRC-NHN / SRC-WSC-BASINS / SRC-GIN / SRC-STA-GW / SRC-NRCAN-FLOOD | "Data Source: Environment and Climate Change Canada" / "Contains information licensed under the Open Government Licence – Canada" | Permitted w/ attribution | STA-GW host currently unresolvable | [8][29][31][32][33][34] |
| SRC-CANSWE / SRC-CIS-ICE / SRC-CRID / SRC-LAKEICE | "Contains information licensed under the Open Government Licence – Canada" | Permitted w/ attribution | Periodic dataset cadence | [8][35][36][37][38] |
| SRC-AB-RIVERS | "Government of Alberta" | **Non-commercial only**; commercial needs written permission | "Authorized users only" gate; intermittent refusal | [10][11] |
| SRC-SK-WSA | "Water Security Agency (Government of Saskatchewan)" | **Non-commercial only**; commercial needs written permission | Scrape-only | [12] |
| SRC-MB-FLOODINFO | "Contains information licensed under the OpenMB Information and Data Use License (Manitoba.ca/OpenMB)" | Permitted w/ attribution | AGOL feed | [13] |
| SRC-MB-HFC | (unspecified) | Uncertain — verify before reuse | HTML/PDF | [14] |
| SRC-BC-ASWS / -FWA / -RFC / -AQUARIUS | "Contains information licensed under the Open Government Licence – British Columbia" | Permitted w/ attribution | AQUARIUS endpoint undocumented | [15][16][17][18] |
| SRC-ON-KIWIS / -OIH / -PGMN | "Contains information licensed under the Open Government Licence – Ontario" | Permitted w/ attribution | KiWIS request/return-field params | [19][20][21][23] |
| SRC-ON-CO | (unspecified) | Uncertain — page moved | HTML/PDF, no API | [22] |
| SRC-QC-VIGILANCE / -GRHQ / -RSESQ | "Gouvernement du Québec" | Permitted w/ attribution | WFS / CKAN | [24][25][26][27] |
| SRC-NL-ADRS | "Contains information licensed under the Open Government Licence – Newfoundland and Labrador" | Permitted w/ attribution | Per-station CSV | [28] |
| SRC-HYDROSHEDS | Per HydroSHEDS Licence (attribute HydroSHEDS/WWF) | Permitted w/ attribution | — | [30] |
| SRC-RIVTEMP | Per-dataset (attribute RivTemp/DataStream) | **Conditional** on dataset | **API key (`x-api-key`), ~2 req/s** | [39] |
| SRC-CIOOS | Per-dataset (CC-BY/OGL/CC0) | Permitted w/ attribution | ERDDAP tabledap | [40] |
| SRC-MET-NORWAY | "Data from MET Norway" | Permitted w/ attribution | **Descriptive User-Agent required** | [41] |
| SRC-OPEN-METEO (+ AQI/ARCHIVE) | "Weather data by Open-Meteo.com" | Permitted w/ attribution (**non-commercial free tier**) | 600/min, 5,000/hr, 10,000/day | [42][46] |

### 10.3 Project licence vs upstream licences

The **project licence** governs WaterPulse's own code and compiled product; it is distinct from every
upstream data licence. Nothing in the project licence can enlarge rights granted by an upstream. Where
an upstream forbids commercial use (AB, SK) or restricts it to a paid plan (Open-Meteo), the project
licence SHALL NOT be represented as conferring commercial rights over that upstream's data.

### 10.4 Posture A — non-commercial (current)

Under the current non-commercial posture, **every** source in the registry is usable subject to its
attribution string and technical limits. AB, SK, and the Open-Meteo free tier are all permissible
here. No source is excluded.

### 10.5 Posture B — hypothetical commercial tier

A commercial tier re-scores each upstream against its commercial terms (Table 10-A, "Commercial?"
column). Commercial-OK: all ECCC/federal (OGL-Canada), MB (OpenMB), BC/ON/NB/NS/PE/NL/YT (OGL-
jurisdiction), QC (CC-BY), MET Norway, CIOOS, HydroSHEDS. Conditional: RivTemp (per-dataset + API key).
Not commercial-OK without action: **AB**, **SK**, **Open-Meteo free tier**, and the **unspecified**
sources (MB-HFC, ON-CO) pending clarification.

### 10.6 Composite most-restrictive analysis (NORMATIVE)

For a commercial tier, the maximum commercially-usable footprint is capped by the **most-restrictive
upstream term** in each jurisdiction/function:

- **Alberta:** commercial use of `SRC-AB-RIVERS` is a **hard blocker** (written permission required).
  Mitigation: use ECCC Datamart AB (409 realtime stations, MEASURED) commercially instead; it is
  OGL-Canada and commercial-OK.
- **Saskatchewan:** commercial use of `SRC-SK-WSA` is a **hard blocker** (written permission; scrape-
  only). Mitigation: use ECCC Datamart SK (150 realtime stations, MEASURED) commercially.
- **Open-Meteo (weather/AQI/archive):** the free tier is **non-commercial only**. Mitigation: purchase a
  paid Open-Meteo plan, or substitute `SRC-ECCC-CITYPAGE` (commercial-OK) and/or `SRC-MET-NORWAY`
  (commercial-OK) for the weather contract.
- **RivTemp:** commercial use is **conditional** per dataset and requires an API key; clear each dataset
  individually.
- **MB-HFC / ON-CO:** licences unspecified; SHALL NOT be redistributed commercially until clarified.

**Bottom line:** with the AB/SK substitutions to ECCC and either a paid Open-Meteo plan or an ECCC/MET
substitution, a commercial tier is achievable across all thirteen provinces/territories using
commercial-OK sources, **without cutting any source** from the non-commercial product. The commercial
gate SHALL enforce these substitutions at Stage 5 (Section 3.3).

---

## 11. Attribution & Citation Requirements

- **AT-1.** Every displayed or exported datum SHALL carry the attribution string mandated for its
  source in Table 10-B. Aggregated views SHALL carry a consolidated credits list covering every
  contributing source.
- **AT-2.** The federal attribution SHALL read **"Data Source: Environment and Climate Change Canada"**
  for MSC/WSC feeds and **"Contains information licensed under the Open Government Licence – Canada"**
  for other federal OGL-Canada datasets, per each source's row.
- **AT-3.** Provincial OGL attributions SHALL name the jurisdiction exactly ("… Open Government
  Licence – British Columbia / Ontario / Newfoundland and Labrador", "OpenMB Information and Data Use
  License", "Gouvernement du Québec").
- **AT-4.** MET Norway SHALL be credited "Data from MET Norway" and accessed with a descriptive
  User-Agent; Open-Meteo SHALL be credited "Weather data by Open-Meteo.com".
- **AT-5.** This standard SHALL be cited as: WaterPulse Data Engineering, "WaterPulse Data-Source
  Standard (DS-STD-2026.1), Part 1," 2026-09-16.

---

## 12. Privacy & FOIP

- The ingested **source feeds carry no personal data** — they are hydrometric, meteorological, and
  geospatial observations about the physical environment, not about identifiable individuals.
- The **Alberta FOIP** notice associated with rivers.alberta.ca pertains to **alert sign-up** (personal
  contact details for flood alerting), **not** to the hydrometric values themselves; WaterPulse does
  not ingest alert-subscription personal data.
- Consequently no privacy-impact assessment is triggered by the data feeds. Should WaterPulse later
  collect user accounts, alert subscriptions, or location, a separate privacy assessment SHALL be
  performed; it is out of scope for this data-source standard.

---

## 13. Security & Authentication

- **Upstream authentication:** none is required for any sanctioned source **except** `SRC-RIVTEMP`,
  which requires a DataStream API key (`x-api-key`, ~2 req/s). No other source in the registry uses
  API keys, OAuth, or credentials.
- **Secrets handling:** the DataStream API key SHALL be stored in the deployment secrets store, never
  in source control or client-side code, and SHALL be transmitted only over TLS.
- **Transport:** all endpoints SHALL be accessed over HTTPS/TLS. Requests SHOULD carry a descriptive
  User-Agent (mandatory for MET Norway) and SHALL honour `Retry-After`.
- **Injection surface:** feeds are read-only pulls; there is no upstream write path. The one removed
  legacy write-style endpoint (ECCC Alberta WaterlevelRecords POST) is discussed in Section 14.

---

## 14. Reliability & Uptime

This section records the observed reliability findings from run `probes-20260916T090344Z` and known
endpoint changes. These are genuine findings, surfaced not hidden.

- **F-1 — Federal groundwater SensorThings DNS-unresolvable (MEASURED).** All three `SRC-STA-GW` probes
  (national, ON, QC) failed with **DNS error**: the officially catalogued host `mon.geosciences.ca`
  did not resolve during testing. This is a real availability/reliability finding. **Mitigation:** GIN
  WMS (`SRC-GIN`, 44 layers, MEASURED) is the working federal groundwater alternative.
- **F-2 — Alberta intermittent connection refusal (MEASURED).** `SRC-AB-RIVERS` exhibited
  **intermittent connection refusal** (bad path → 404). Combined with its non-commercial licence, this
  makes ECCC Datamart AB the reliable sanctioned AB path.
- **F-3 — ECCC legacy Alberta WaterlevelRecords POST removed (Apr 2026).** The legacy ECCC Alberta
  `WaterlevelRecords` POST endpoint was **removed in April 2026**. Pipelines SHALL NOT depend on it;
  the sanctioned AB realtime path is the Datamart bulk CSV.
- **F-4 — Conservation Ontario page moved (HTTP 404, MEASURED).** `SRC-ON-CO` returned 404; the page
  moved and there is no API. **Mitigation:** treat as human-readable context; rely on ECCC/provincial
  feeds for ON flood signal.
- **F-5 — RivTemp requires a key (HTTP 401, MEASURED).** Not an uptime failure; documented auth
  prerequisite (Section 13).
- **F-6 — `ok_empty` endpoints.** `SRC-ECCC-WATERPRED`, `SRC-CRID`, and `SRC-LAKEICE` were reachable but
  returned no rows/file link on the light sample; they require deeper queries and SHOULD not be marked
  "down".
- **Latency reliability:** AB/ON Datamart (7,950 / 7,238 ms) and the archive/Zenodo endpoints are the
  slow tail; schedulers SHOULD apply generous timeouts and retries with backoff for these.

---

## 15. Retention & Archival

- **Validated history (HYDAT backbone):** retained indefinitely as the authoritative archive; refreshed
  each quarter and version-stamped (Section 9).
- **Realtime cache (Datamart / provincial):** retained as provisional until superseded by validated
  HYDAT for the same station-time, after which the validated value is authoritative; provisional
  records SHOULD be retained for audit/lineage rather than deleted.
- **Provenance metadata:** SHALL be retained for the life of any datum it describes (Source ID, licence,
  fetch time, run_id).
- **Enrichment datasets (snow/ice/climate/reanalysis):** retained per their release versions; superseded
  releases MAY be archived rather than overwritten to preserve reproducibility of past reports.

---

## 16. Change Management, Deprecation & Review Cadence

- **Registry change control.** Adding, removing, or re-roling a source SHALL be a versioned change to
  the registry (Section 4) accompanied by a fresh reconnaissance `run_id`.
- **Deprecation.** A source that becomes unavailable (e.g., F-1 SensorThings DNS, F-3 removed AB POST,
  F-4 ON-CO 404) SHALL be marked deprecated/at-risk in the registry with its mitigation, not silently
  dropped.
- **PID.** Before this standard leaves **Draft**, the persistent identifier (currently TBD) SHALL be
  minted and recorded in the front matter of every Part.
- **Review cadence.** This standard SHALL be reviewed at least **quarterly**, aligned with the HYDAT
  release cycle, and additionally whenever a monitored endpoint changes materially. Each review SHALL
  re-run the sanctioned probe suite and update measured figures with the new `run_id`.

---

## 17. Risk Register

Likelihood/Impact are qualitative (L/M/H). All risks carry a mitigation.

| ID | Category | Risk | L | I | Mitigation |
|----|----------|------|---|---|------------|
| R-1 | Licensing | Commercial use of AB (`SRC-AB-RIVERS`) without written permission | M | H | Use ECCC Datamart AB commercially; gate AB provincial feed to non-commercial (C-5) |
| R-2 | Licensing | Commercial use of SK (`SRC-SK-WSA`) without written permission | M | H | Use ECCC Datamart SK commercially; gate SK scrape to non-commercial |
| R-3 | Licensing | Open-Meteo free tier used commercially | M | H | Paid plan or substitute City Page / MET Norway at Stage 5 |
| R-4 | Licensing | MB-HFC / ON-CO unspecified licences redistributed | L | M | Treat as context-only until clarified; do not redistribute |
| R-5 | Availability | Federal GW SensorThings host unresolvable (F-1) | H | M | GIN WMS substitute; mark deprecated/at-risk |
| R-6 | Availability | Alberta intermittent refusal (F-2) / legacy POST removed (F-3) | H | M | Datamart AB as sanctioned path |
| R-7 | Availability | AB/ON Datamart slow pulls (7–8 s) cause timeouts | M | M | Generous timeouts, backoff, staggered scheduling |
| R-8 | Availability | ECCC acceptable-use ceiling breach (~1 req/s) triggers throttling/contact | M | M | Rate-limit ingestion; no cache-bypass headers; monitor request volume |
| R-9 | Quality | Provisional Datamart value shown as validated | M | M | Provisional badge + HYDAT reconciliation (C-6) |
| R-10 | Quality | `ok_empty` sources (WATERPRED/CRID/LAKEICE) treated as coverage | M | L | Deeper queries; do not advertise as populated |
| R-11 | Security | DataStream API key leaked | L | H | Secrets store, TLS, no client-side exposure |
| R-12 | Privacy | Confusing FOIP alert-signup with data feeds | L | L | Documented: feeds carry no personal data (Section 12) |
| R-13 | Attribution | Missing/incorrect attribution string | M | M | Enforce Table 10-B strings at Stage 5 (C-3) |

---

## 18. References

All URLs Accessed: 2026-09-16. Measured figures derive from run `probes-20260916T090344Z`; advertised
items are labelled as such in the body.

[1] Meteorological Service of Canada, "MSC Datamart — Hydrometric data (CSV)," Environment and Climate
Change Canada. [Online]. Available: https://dd.weather.gc.ca/hydrometric/ Accessed: 2026-09-16.

[2] Meteorological Service of Canada, "MSC GeoMet — OGC API (Features/EDR)," Environment and Climate
Change Canada. [Online]. Available: https://api.weather.gc.ca/ Accessed: 2026-09-16.

[3] Water Survey of Canada, "HYDAT — National Water Data Archive," Environment and Climate Change
Canada. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/monitoring/survey/data-products-services/national-archive-hydat.html Accessed: 2026-09-16.

[4] Meteorological Service of Canada, "City Page Weather (XML) and site catalogue," Environment and
Climate Change Canada. [Online]. Available: https://dd.weather.gc.ca/citypage_weather/ Accessed: 2026-09-16.

[5] Environment and Climate Change Canada, "Air Quality Health Index (AQHI) — observations via GeoMet,"
[Online]. Available: https://api.weather.gc.ca/collections/aqhi-observations-realtime Accessed: 2026-09-16.

[6] Environment and Climate Change Canada, "GeoMet-Climate — climate stations and daily/hourly/monthly
observations; RDPA/CaPA," [Online]. Available: https://api.weather.gc.ca/ Accessed: 2026-09-16.

[7] Environment and Climate Change Canada, "GeoMet water-prediction collections," [Online]. Available:
https://api.weather.gc.ca/ Accessed: 2026-09-16.

[8] Government of Canada, "Open Government Licence – Canada 2.0," [Online]. Available:
https://open.canada.ca/en/open-government-licence-canada Accessed: 2026-09-16.

[9] Meteorological Service of Canada, "MSC/GeoMet End-use Licence and acceptable-use policy (v2.1.1),"
Environment and Climate Change Canada. [Online]. Available: https://eccc-msc.github.io/open-data/msc-data/readme_en/ Accessed: 2026-09-16.

[10] Government of Alberta, "Alberta River Basins (rivers.alberta.ca)," [Online]. Available:
https://rivers.alberta.ca/ Accessed: 2026-09-16.

[11] Government of Alberta, "Copyright and disclaimer / FOIP," [Online]. Available:
https://www.alberta.ca/copyright.aspx Accessed: 2026-09-16.

[12] Water Security Agency, "Saskatchewan water data (wsask.ca)," Government of Saskatchewan. [Online].
Available: https://www.wsask.ca/ Accessed: 2026-09-16.

[13] Government of Manitoba, "FloodInfo and the OpenMB Information and Data Use Licence," [Online].
Available: https://www.manitoba.ca/openmb/ Accessed: 2026-09-16.

[14] Government of Manitoba, "Hydrologic Forecast Centre," [Online]. Available:
https://www.gov.mb.ca/mit/floodinfo/ Accessed: 2026-09-16.

[15] Government of British Columbia, "Automated Snow Weather Stations (ASWS) — snow survey," [Online].
Available: https://www2.gov.bc.ca/gov/content/environment/air-land-water/water/water-science-data/water-data-tools/snow-survey-data Accessed: 2026-09-16.

[16] Government of British Columbia, "Freshwater Atlas," [Online]. Available:
https://www2.gov.bc.ca/gov/content/data/geographic-data-services/topographic-data/freshwater Accessed: 2026-09-16.

[17] Government of British Columbia, "River Forecast Centre," [Online]. Available:
https://www2.gov.bc.ca/gov/content/environment/air-land-water/water/drought-flooding-dikes-dams/river-forecast-centre Accessed: 2026-09-16.

[18] Government of British Columbia, "Open Government Licence – British Columbia 2.0," [Online].
Available: https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc Accessed: 2026-09-16.

[19] Ontario Surface Water Monitoring Centre, "KiWIS (WISKI) web services," Government of Ontario.
[Online]. Available: https://www.ontario.ca/page/surface-water-monitoring Accessed: 2026-09-16.

[20] Government of Ontario, "Ontario Integrated Hydrology data," [Online]. Available:
https://data.ontario.ca/ Accessed: 2026-09-16.

[21] Government of Ontario, "Provincial Groundwater Monitoring Network (PGMN)," [Online]. Available:
https://data.ontario.ca/dataset/provincial-groundwater-monitoring-network-pgmn-wells Accessed: 2026-09-16.

[22] Conservation Ontario, "Flood warnings / forecasting," [Online]. Available:
https://conservationontario.ca/ Accessed: 2026-09-16.

[23] Government of Ontario, "Open Government Licence – Ontario," [Online]. Available:
https://www.ontario.ca/page/open-government-licence-ontario Accessed: 2026-09-16.

[24] Gouvernement du Québec, "Vigilance — surveillance hydrologique (WFS)," [Online]. Available:
https://www.cehq.gouv.qc.ca/ Accessed: 2026-09-16.

[25] Gouvernement du Québec, "Géobase du réseau hydrographique du Québec (GRHQ)," [Online]. Available:
https://www.donneesquebec.ca/ Accessed: 2026-09-16.

[26] Gouvernement du Québec, "Réseau de suivi des eaux souterraines du Québec (RSESQ)," [Online].
Available: https://www.donneesquebec.ca/ Accessed: 2026-09-16.

[27] Gouvernement du Québec, "Licence Creative Commons Attribution 4.0 (Québec) — Données Québec,"
[Online]. Available: https://www.donneesquebec.ca/licence/ Accessed: 2026-09-16.

[28] Government of Newfoundland and Labrador, "Water Resources — Advanced Data Retrieval System (ADRS),"
[Online]. Available: https://www.gov.nl.ca/ecc/waterres/ Accessed: 2026-09-16.

[29] Natural Resources Canada, "National Hydro Network (NHN)," [Online]. Available:
https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977 Accessed: 2026-09-16.

[30] WWF / HydroSHEDS, "HydroBASINS / HydroSHEDS," [Online]. Available: https://www.hydrosheds.org/
Accessed: 2026-09-16.

[31] Water Survey of Canada, "Hydrometric gauge drainage-basin polygons," Environment and Climate
Change Canada. [Online]. Available: https://open.canada.ca/ Accessed: 2026-09-16.

[32] Natural Resources Canada, "Groundwater Information Network (GIN)," [Online]. Available:
https://gin.gw-info.net/ Accessed: 2026-09-16.

[33] Geological Survey of Canada, "Groundwater monitoring — OGC SensorThings API (mon.geosciences.ca),"
Natural Resources Canada. [Online]. Available: https://mon.geosciences.ca/ Accessed: 2026-09-16.

[34] Natural Resources Canada, "Flood Hazard Identification and Mapping Program (FHIMP) hub," [Online].
Available: https://natural-resources.canada.ca/science-data/science-research/flood-mapping Accessed: 2026-09-16.

[35] Vionnet et al., "CanSWE — Canadian historical Snow Water Equivalent dataset," Zenodo. [Online].
Available: https://zenodo.org/record/CanSWE Accessed: 2026-09-16.

[36] Canadian Ice Service, "Ice thickness archive," Environment and Climate Change Canada. [Online].
Available: https://www.canada.ca/en/environment-climate-change/services/ice-forecasts-observations.html Accessed: 2026-09-16.

[37] Environment and Climate Change Canada, "Canadian River Ice Database (CRID)," [Online]. Available:
https://open.canada.ca/ Accessed: 2026-09-16.

[38] Environment and Climate Change Canada, "Canadian Lake Ice Database," [Online]. Available:
https://open.canada.ca/ Accessed: 2026-09-16.

[39] The Gordon Foundation, "DataStream (OData v4 API) — RivTemp datasets," [Online]. Available:
https://gordonfoundation.ca/initiatives/datastream/ Accessed: 2026-09-16.

[40] CIOOS Atlantic, "ERDDAP data server," Canadian Integrated Ocean Observing System. [Online].
Available: https://cioosatlantic.ca/erddap/ Accessed: 2026-09-16.

[41] MET Norway, "Locationforecast (compact) — Weather API," [Online]. Available:
https://api.met.no/weatherapi/locationforecast/2.0/ Accessed: 2026-09-16.

[42] Open-Meteo, "Open-Meteo Weather / Air Quality / Historical (ERA5) APIs," [Online]. Available:
https://open-meteo.com/ Accessed: 2026-09-16.

[43] S. Bradner, "Key words for use in RFCs to Indicate Requirement Levels," RFC 2119, IETF, Mar. 1997.
[Online]. Available: https://www.rfc-editor.org/rfc/rfc2119 Accessed: 2026-09-16.

[44] Linux Foundation, "SPDX License List," [Online]. Available: https://spdx.org/licenses/ Accessed:
2026-09-16.

[45] Open Geospatial Consortium, "OGC API — Features (Part 1: Core) and OGC API — Environmental Data
Retrieval," [Online]. Available: https://ogcapi.ogc.org/ Accessed: 2026-09-16.

[46] Creative Commons, "Attribution 4.0 International (CC BY 4.0)," [Online]. Available:
https://creativecommons.org/licenses/by/4.0/ Accessed: 2026-09-16.

---

*End of DS-STD-2026.1 Part 1 — Standard & Reconnaissance. Measured figures are from run
`probes-20260916T090344Z` (2026-09-16); advertised figures are labelled as such. Cite as: WaterPulse
Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1," 2026-09-16.*
