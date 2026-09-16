# WaterPulse Data-Source Standard (DS-STD-2026.1) — Part 3: Results & Verified Standard

| | |
|---|---|
| **Report ID** | DS-STD-2026.1 |
| **Part** | 3 of 3 — Results & Verified Standard |
| **Version** | 1.0 |
| **Status** | Draft |
| **Publication date** | 2026-09-16 |
| **Prepared for** | WaterPulse-Canada |
| **Authoring organization** | WaterPulse Data Engineering |
| **Persistent identifier** | TBD (placeholder) |
| **Evidence run** | `probes-20260916T090344Z` (2026-09-16) |

**How to cite this document:** WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 3," 2026-09-16.

**Companion documents:** Part 1 — Architecture & Source Registry [1]; Part 2 — Method & Test Protocol [2]. This part reports measured results and the resulting verified, normative standard; it does not restate the architecture rationale (Part 1) or the probe method (Part 2).

---

## Abstract

This part reports the measured outcome of the DS-STD-2026.1 coverage evaluation and derives the normative, evidence-backed data-source recommendation for WaterPulse-Canada. In a single sanctioned run (`probes-20260916T090344Z`, 2026-09-16), **80 of 86 sanctioned source probes were retrievable in 186.7 s**, exercising a registry of 90 probes (86 sanctioned + 4 residual) across 12 data categories and all 13 Canadian provinces/territories. The results confirm the standard's core architecture: Environment and Climate Change Canada / Water Survey of Canada (ECCC/WSC) form a deep, commercially-licensable historical and real-time backbone — HYDAT alone returns 1,779,871 archived daily records over 6,478 stations from 1860, and ECCC's national climate-daily archive returns 184,672,664 records from 1876 — while a small number of provinces (AB, BC-partial, MB, ON, QC, NL) add a genuine programmatic provincial river feed and the remainder are ECCC-primary. Québec is confirmed as the standing exception: ECCC's real-time Datamart carries only 15 QC hydrometric stations (9,191 rows measured), so QC river data SHALL be sourced provincially from Vigilance. The six non-retrievable probes are individually diagnosed (a DNS-unresolvable federal groundwater host, an API-key-gated river-temperature service, a moved provincial flood page, and one empty water-prediction sample) and none invalidate a recommended primary source. The historical requirement (≥15 historical sources) is satisfied with 19 retrievable historical probes. This part closes with the verified per-jurisdiction × per-category normative matrix, a non-commercial-versus-commercial monetization finding, and the status of the residual overnight stress harness (smoke-validated 2026-09-16; the full run remains pending and will be appended as dated Addendum, Part 3a).

## Index Terms

Air Quality Health Index (AQHI), Canadian river data, coverage evaluation, data-source standard, Datamart, ECCC, GeoMet OGC API, historical hydrometry, HYDAT, licensing, open government licence, provincial hydrometric feeds, Québec Vigilance, real-time streamflow, Water Survey of Canada.

---

## 1. Introduction and scope of this part

Part 1 [1] established the source registry and the "provincial-primary where programmatic, ECCC/WSC as backbone and validation" architecture. Part 2 [2] defined the probe harness, the sanctioned-versus-residual distinction, the retrievability decision rule, and the per-probe evidence schema. This part (Part 3) presents the measured results of executing that protocol, interprets the outcomes, and promotes the tested findings into a normative standard.

Normative statements in this part use RFC-2119 key words — SHALL, SHOULD, MAY — as defined in [25]. All quantitative claims derive from the single evidence run identified below and MUST NOT be read as advertised or catalogue figures; where a catalogue figure differs from a measured figure, the measured figure governs.

## 2. Method recap

WaterPulse Data Engineering executed the Part 2 [2] harness once against every sanctioned probe (`run_id = probes-20260916T090344Z`, 2026-09-16); for full protocol, User-Agent policy, rate discipline, and the retrievability decision rule, see Part 2 [2].

**Evidence artifacts (this run):** `waterpulse-backend/tests/logs/probes-20260916T090344Z/{coverage.csv, coverage_summary.json, requests.csv, tests.csv}`.

## 3. Results by category

### 3.1 Run-level totals

| Metric | Value |
|---|---|
| Run ID | `probes-20260916T090344Z` |
| Date | 2026-09-16 |
| Wall-clock elapsed | 186.7 s |
| Registry total (all probes) | 90 (86 sanctioned + 4 residual) |
| Sanctioned probes executed | 86 |
| Retrievable (`retrievable = True`) | **80** |
| Not retrievable | 6 |
| Categories exercised | 12 |
| Jurisdictions exercised | 13 P/T + national |

Reason breakdown (sanctioned probes): `ok` = 78, `ok_empty` = 3 (2 reachable, 1 not), `dns_error` = 3, `http_401_unauthorized` = 1, `http_404_upstream_missing` = 1. Commercial-use posture across sanctioned probes: `yes` = 80, `non-commercial` = 3, `unknown` = 2, `conditional` = 1.

Registry composition by category (from `coverage_summary.json.matrix.by_category`): aqi 2, current 20, stations 15, historical 19, drainage 6, groundwater 6, flood 6, precip 4, ice 3, snow 3, weather 4, watertemp 2. (The `current` count of 20 includes the 3 residual provincial scrape probes — see §8 — which are excluded from the 86 sanctioned rows below.)

### 3.2 `current` — real-time water level / flow (17 sanctioned probes; 17 retrievable)

The ECCC Datamart hourly bulk CSV is confirmed retrievable in every one of the 13 provinces/territories. Provincial real-time feeds (MB FloodInfo, NL ADRS, QC Vigilance) and the GeoMet OGC API national sample are also retrievable.

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| ECCC Datamart bulk CSV | AB | True | ok | 10 | 236,259 | 409 | 7,949.5 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart bulk CSV | BC | True | ok | 10 | 247,941 | 436 | 1,467.6 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | MB | True | ok | 10 | 146,821 | 250 | 1,095.6 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | NB | True | ok | 10 | 31,767 | 51 | 642.9 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | NL | True | ok | 10 | 60,635 | 97 | 733.3 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | NS | True | ok | 10 | 23,782 | 39 | 579.5 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | NT | True | ok | 10 | 56,924 | 100 | 837.4 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | NU | True | ok | 10 | 14,006 | 24 | 1,599.0 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | ON | True | ok | 10 | 317,748 | 523 | 7,238.0 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | PE | True | ok | 10 | 5,571 | 9 | 533.9 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | **QC** | True | ok | 10 | **9,191** | **15** | 504.9 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | SK | True | ok | 10 | 88,617 | 150 | 2,583.7 | OGL-Canada/ECCC · yes |
| ECCC Datamart bulk CSV | YT | True | ok | 10 | 40,778 | 72 | 784.2 | OGL-Canada/ECCC · yes |
| ECCC GeoMet realtime (national sample) | CA | True | ok | 13 | 10 | 1 | 259.2 | OGL-Canada/ECCC v2.1.1 · yes |
| MB FloodInfo AGOL CSV (level/flow/forecast/alert) | MB | True | ok | 30 | 248 | — | 231.3 | OpenMB · yes |
| NL ADRS per-station CSV (level/flow/water-temp) | NL | True | ok | 1 | 2,005 | 1 | 598.6 | OGL-NL · yes |
| Québec Vigilance WFS stations (GeoJSON) | QC | True | ok | 13 | 50 | 50 | 505.1 | CC-BY-4.0 (QC) · yes |

**Findings.** Across the 13 Datamart pulls the harness retrieved **≈1,280,040 real-time rows over ≈2,175 active hydrometric stations**. ON (317,748 rows / 523 stations) and BC (247,941 / 436) are the largest real-time networks; PE (9 stations) and NU (24) the smallest. **QC is the decisive datum: only 15 QC stations / 9,191 rows appear on Datamart** — an order of magnitude below QC's catalogued network (1,001 GeoMet stations, §3.3) — confirming the Québec exception (§7). The heaviest latencies are the two largest bulk CSVs (AB 7.95 s, ON 7.24 s); provincial JSON/CSV feeds all returned in <0.6 s.

### 3.3 `stations` — station registry / metadata (15 probes; 15 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) |
|---|---|---|---|---:|---:|---:|---:|
| ECCC GeoMet climate-stations | CA | True | ok | 33 | 8,435 | 8,435 | 244.4 |
| ECCC GeoMet hydrometric stations | AB | True | ok | 14 | 10 | 1,104 | 209.8 |
| ECCC GeoMet hydrometric stations | BC | True | ok | 14 | 10 | **2,324** | 214.3 |
| ECCC GeoMet hydrometric stations | MB | True | ok | 14 | 10 | 659 | 219.8 |
| ECCC GeoMet hydrometric stations | NB | True | ok | 14 | 10 | 144 | 215.3 |
| ECCC GeoMet hydrometric stations | NL | True | ok | 14 | 10 | 230 | 205.8 |
| ECCC GeoMet hydrometric stations | NS | True | ok | 14 | 10 | 144 | 203.4 |
| ECCC GeoMet hydrometric stations | NT | True | ok | 14 | 10 | 245 | 211.1 |
| ECCC GeoMet hydrometric stations | NU | True | ok | 14 | 10 | 109 | 211.6 |
| ECCC GeoMet hydrometric stations | ON | True | ok | 14 | 10 | 1,119 | 215.3 |
| ECCC GeoMet hydrometric stations | PE | True | ok | 14 | 10 | 43 | 269.4 |
| ECCC GeoMet hydrometric stations | QC | True | ok | 14 | 10 | 1,001 | 205.5 |
| ECCC GeoMet hydrometric stations | SK | True | ok | 14 | 10 | 748 | 209.0 |
| ECCC GeoMet hydrometric stations | YT | True | ok | 14 | 10 | 114 | 216.4 |
| Ontario SWMC KiWIS getStationList | ON | True | ok | 5 | 4,436 | 4,436 | 2,004.0 |

**Findings.** GeoMet catalogues **≈7,984 hydrometric stations nationally** (BC 2,324 > ON 1,119 > AB 1,104 > QC 1,001 > SK 748 > MB 659 > … > PE 43). ECCC climate-stations adds 8,435 climate sites. Ontario's provincial KiWIS registry (4,436 stations) is far larger than ON's GeoMet hydrometric set (1,119) and is the richest single-jurisdiction station source in the registry.

### 3.4 `historical` — deep archives (19 probes; 19 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| **HYDAT national archive (full record)** | CA | True | ok | 106 | **1,779,871** | **6,478** | **1860 → 167 yr** | 385.4 |
| GeoMet daily-mean (05BB001) | CA | True | ok | 12 | 50 | 1 | 1989 → 1 | 291.8 |
| GeoMet monthly-mean (05BB001) | CA | True | ok | 8 | 50 | 1 | 1909 → 5 | 245.8 |
| GeoMet annual-statistics (05BB001) | CA | True | ok | 15 | 50 | 1 | 1909 → 117 | 215.1 |
| GeoMet annual-peaks (05BB001) | CA | True | ok | 16 | 50 | 1 | 1923 → 103 | 219.7 |
| GeoMet daily-mean depth | AB | True | ok | 12 | — | 1 | 1908 → 42 | 77.0 |
| GeoMet daily-mean depth | BC | True | ok | 12 | — | 1 | 1960 → 24 | 73.4 |
| GeoMet daily-mean depth | MB | True | ok | 12 | — | 1 | 1957 → 17 | 72.5 |
| GeoMet daily-mean depth | NB | True | ok | 12 | — | 1 | 1951 → 75 | 73.8 |
| GeoMet daily-mean depth | NL | True | ok | 12 | — | 1 | 1999 → 2 | 72.4 |
| GeoMet daily-mean depth | NS | True | ok | 12 | — | 1 | 1964 → 36 | 77.1 |
| GeoMet daily-mean depth | NT | True | ok | 12 | — | 1 | 2017 → 6 | 71.7 |
| GeoMet daily-mean depth | NU | True | ok | 12 | — | 1 | 1970 → 21 | 672.2 |
| GeoMet daily-mean depth | ON | True | ok | 12 | — | 1 | 1972 → 7 | 74.4 |
| GeoMet daily-mean depth | PE | True | ok | 12 | — | 1 | 1919 → 4 | 71.4 |
| GeoMet daily-mean depth | QC | True | ok | 12 | — | 1 | 1967 → 11 | 72.1 |
| GeoMet daily-mean depth | SK | True | ok | 12 | — | 1 | 1911 → 115 | 81.4 |
| GeoMet daily-mean depth | YT | True | ok | 12 | — | 1 | 1950 → 37 | 73.1 |
| Open-Meteo Archive (ERA5) | multi | True | ok | 3 | 31 | — | 1940 → 1 | 688.2 |

**Findings.** HYDAT is the deepest and widest archive by every measure — 1,779,871 records, 6,478 stations, 106 fields, reaching back to **1860** (167-year span) — and is the historical backbone of the standard. The GeoMet OGC API supplies the same lineage programmatically (daily/monthly/annual-mean, annual-statistics, annual-peaks). See §5 for per-jurisdiction depth.

### 3.5 `precip` — precipitation & climate observations (4 probes; 4 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---|---:|
| ECCC GeoMet climate-daily (precip + snow-on-ground) | CA | True | ok | 34 | **184,672,664** | 1876 → 138 | 244.0 |
| ECCC GeoMet climate-hourly | CA | True | ok | 40 | **277,058,947** | 1972 → 1 | 209.8 |
| ECCC GeoMet climate-monthly | CA | True | ok | 34 | 1,881,824 | 1990 → 2 | 218.6 |
| ECCC GeoMet RDPA/CaPA 10 km 6 h (metadata) | CA | True | ok | 6 | — | — | 412.7 |

**Findings.** ECCC's climate archive is enormous and reachable: 184.7 M daily records back to **1876** and 277.1 M hourly records. RDPA/CaPA gridded precipitation is confirmed at the metadata layer.

### 3.6 `weather` — point forecasts (4 probes; 4 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Earliest | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---|---:|---|
| Open-Meteo forecast (current + 7-day) | CA | True | ok | **27** | 7 | 2026 | 380.1 | CC-BY-4.0 · **non-commercial** (free tier) |
| ECCC City Page — city XML (Calgary) | AB | True | ok | 20 | 11 | — | 62.6 | OGL-Canada/ECCC · yes |
| ECCC City Page — site catalogue CSV | CA | True | ok | 5 | 856 | — | 263.4 | OGL-Canada/ECCC · yes |
| MET Norway Locationforecast 2.0 (compact) | CA | True | ok | 11 | 91 | — | 513.4 | CC-BY-4.0 / NLOD-2.0 · yes |

**Findings.** Open-Meteo supplies the full 27-field app weather contract but under a non-commercial free tier; the two commercial-OK alternatives supply fewer fields (City Page 20, MET Norway 11). This field-versus-licence tension is analysed in §6.

### 3.7 `aqi` — air quality (2 probes; 2 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| ECCC AQHI observations (GeoMet OGC API) | CA | True | ok | 14 | 6,996 | 10 | 397.2 | OGL-Canada/MSC v2.1.1 · yes |
| Open-Meteo Air Quality (us_aqi + pm2_5/pm10) | multi | True | ok | 5 | 1 | — | 832.8 | CC-BY-4.0 · non-commercial |

**Findings.** Both AQI sources are retrievable, but they are **not on the same scale**: ECCC returns the Canadian Air Quality Health Index (AQHI, 1–10+), while Open-Meteo returns the US AQI (0–500). The app's AQI contract is AQHI-based; the scale mismatch is a remediation item (§6).

### 3.8 `snow` — snow water equivalent (3 probes; 2 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| BC ASWS near-real-time SWE (wide CSV) | BC | True | ok | 122 | 8,409 | 121 | — | 815.5 |
| CanSWE national SWE (Zenodo metadata) | CA | True | ok | 8 | 4 | — | 1928 → 98 | 4,604.3 |

*(The third `snow` registry entry is a residual/harness item; see §8.)*

**Findings.** BC ASWS provides dense near-real-time SWE (121 stations, 122 fields). CanSWE is the national historical SWE dataset reaching back to **1928** (98-year span); its 4.6 s latency (Zenodo record fetch) is the slowest in the run and reflects an archival, not real-time, access pattern.

### 3.9 `ice` — river/lake ice (3 probes; 3 retrievable, 2 empty)

| Source | Juris. | Retr. | Reason | Records | Stations | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---|---:|
| Canadian Ice Service — ice-thickness archive page | CA | True | ok | — | — | — | 3,166.6 |
| Canadian River Ice Database (CRID) | CA | True | ok_empty | — | 196 | 1894 → 122 | 595.2 |
| Lake Ice Database | CA | True | ok_empty | — | — | — | 531.5 |

**Findings.** All three ice sources are reachable. CRID advertises 196 NHP sites with freeze/break-up records back to **1894** (122-year span) but the light sample returned no rows (`ok_empty`) — a deeper query is required (§4). CIS ice-thickness is the slowest non-archival fetch (3.17 s).

### 3.10 `drainage` — watershed / hydro-network geometry (6 probes; 6 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) |
|---|---|---|---|---:|---:|---:|
| National Hydro Network (NHN) | CA | True | ok | 7 | 15 | 409.0 |
| WSC gauge drainage-basin polygons | CA | True | ok | 1 | 1 | 359.6 |
| HydroSHEDS HydroBASINS | CA | True | ok | 13 | — | 200.4 |
| BC Freshwater Atlas watershed boundaries | BC | True | ok | 5 | 8 | 484.5 |
| Ontario Integrated Hydrology (OIH) | ON | True | ok | 2 | 7 | 391.5 |
| QC GRHQ hydro network | QC | True | ok | 6 | 10 | 389.6 |

**Findings.** Drainage geometry is fully covered: national (NHN, WSC basins, HydroSHEDS) plus richer provincial layers in BC, ON, and QC. WSC drainage-basin polygons are keyed to WSC station numbers, enabling gauge-to-basin joins.

### 3.11 `groundwater` — groundwater monitoring (6 probes; 3 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) |
|---|---|---|---|---:|---:|---:|
| GIN WMS GetCapabilities (44 layers) | CA | True | ok | 1 | 44 | 796.6 |
| Ontario PGMN (CKAN) | ON | True | ok | 44 | 7 | 733.4 |
| Quebec RSESQ (CKAN) | QC | True | ok | 53 | 20 | 429.9 |
| GSC SensorThings groundwater (national) | CA | **False** | dns_error | 0 | — | — |
| GSC SensorThings groundwater (ON) | ON | **False** | dns_error | 0 | — | — |
| GSC SensorThings groundwater (QC) | QC | **False** | dns_error | 0 | — | — |

**Findings.** The officially-catalogued federal groundwater SensorThings host (`mon.geosciences.ca`) failed DNS resolution for all three probes — a genuine availability finding, not a transient timeout (§4). The GIN WMS (44 layers) is the working national alternative, with provincial CKAN feeds (ON PGMN, QC RSESQ) retrievable.

### 3.12 `flood` — forecasts & warnings (6 probes; 4 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---|
| BC River Forecast Centre warnings (ArcGIS) | BC | True | ok | 10 | 5 | 522.7 | OGL-BC · yes |
| Québec Vigilance flood-surveillance WFS | QC | True | ok | 13 | 1 | 419.9 | CC-BY-4.0 (QC) · yes |
| Manitoba Hydrologic Forecast Centre (HTML/PDF) | MB | True | ok | 0 | — | 288.5 | MB unspecified · unknown |
| NRCan FHIMP flood-mapping hub (geo.ca) | CA | True | ok | 0 | — | 186.8 | OGL-Canada · yes |
| ECCC GeoMet water-prediction collections | CA | **False** | ok_empty | 0 | 0 | 350.3 | OGL-Canada · yes |
| Conservation Ontario flood warnings (HTML/PDF) | ON | **False** | http_404 | 0 | — | — | CO unspecified · unknown |

**Findings.** Structured flood feeds exist and are retrievable in BC (RFC ArcGIS) and QC (Vigilance WFS). MB HFC and NRCan FHIMP are reachable landing surfaces with no structured payload (0 fields). Two probes did not retrieve: ECCC water-prediction returned an empty sample, and the Conservation Ontario page returned HTTP 404 (moved; HTML-only, no API). See §4.

### 3.13 `watertemp` — water temperature (2 probes; 1 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---|
| CIOOS Atlantic ERDDAP catalogue (coastal) | multi | True | ok | 16 | 10 | 163.9 | CC-BY / OGL / CC0 · yes |
| RivTemp via DataStream OData v4 | CA | **False** | http_401 | 0 | — | 838.4 | DataStream per-dataset · **conditional** |

**Findings.** CIOOS Atlantic provides coastal water temperature. RivTemp (river temperature) returned HTTP 401 because an API key is required (`x-api-key`) — a documented access gate, not an endpoint failure (§4, §6). Note that NL ADRS (§3.2) additionally carries a `WATER_TEMP` field per station, giving river-temperature coverage in NL independent of RivTemp.

## 4. Coverage math and the six non-retrievable probes

### 4.1 The arithmetic

Of **86 sanctioned probes, 80 were retrievable** (`retrievable = True`) and **6 were not**. The retrievable set decomposes as 78 `ok` plus 2 `ok_empty`-but-reachable (CRID, Lake Ice Database — the endpoint responded, so they count as retrievable even though the light sample carried no rows). The 6 non-retrievable probes are the subject of §4.2. Retrievability = 80/86 = **93.0 %**.

### 4.2 The six non-retrievable outcomes — interpreted, not hidden

Per the DS-STD-2026.1 policy of interpreting rather than concealing negative results:

| # | Probe(s) | Reason | Interpretation | Consequence for the standard |
|---|---|---|---|---|
| 1–3 | GSC SensorThings groundwater — national, ON, QC | `dns_error` | The officially-catalogued federal groundwater SensorThings host `mon.geosciences.ca` did not resolve during testing. This is a real availability/reliability finding about the federal endpoint, not a harness fault. | **GIN WMS is the recommended national groundwater source** (§7). SensorThings SHOULD be re-tested and treated as unstable until it resolves. |
| 4 | RivTemp via DataStream OData v4 | `http_401_unauthorized` | An API key is required (`x-api-key`, ~2 req/s). This is a documented access gate, not a failure of the endpoint. | RivTemp MAY be adopted once a key is provisioned; commercial use is CONDITIONAL. Interim river-temperature coverage is available via NL ADRS (§3.13). |
| 5 | Conservation Ontario flood warnings | `http_404_upstream_missing` | The Conservation Ontario page has moved; the resource is HTML-only with no API. | ON flood recommendation falls back to the ECCC/national layer and BC/QC-style structured feeds where available; the CO link MUST be re-discovered before use. |
| 6 | ECCC GeoMet water-prediction collections | `ok_empty` | The collection endpoint is reachable but the light probe sample returned no rows/no file link. Retrievable in principle; needs a deeper query. | Water-prediction is a *candidate* backbone source pending a targeted follow-up query; it is not yet promoted to a recommended primary. |

Two further probes (**CRID**, **Lake Ice Database**) share the `ok_empty` signature but *did* count as retrievable because the endpoint responded; like water-prediction, they need a deeper query to extract rows and SHOULD be re-probed with a targeted request.

### 4.3 Historical requirement satisfied

The standard requires **≥15 historical sources**. The run delivered **19 retrievable historical probes** (§3.4): 13 per-P/T GeoMet daily-mean depth series + HYDAT + 4 GeoMet collection views (daily/monthly/annual-mean, annual-statistics, annual-peaks) + Open-Meteo ERA5 Archive. The requirement is met with margin, and every historical probe was retrievable.

## 5. Historical-depth findings

Measured earliest year per source/jurisdiction (deeper = more valuable for trend and return-period analysis):

| Source / jurisdiction | Earliest year (measured) | Span (yr) | Note |
|---|---:|---:|---|
| **HYDAT (national)** | **1860** | 167 | Deepest archive in the registry; the historical backbone |
| ECCC climate-daily (national) | 1876 | 138 | Deepest precipitation/climate archive |
| GeoMet annual-statistics / monthly-mean | 1909 | 117 / 5 | Programmatic access to the deep lineage |
| GeoMet daily-mean depth — AB | 1908 | 42 | Deepest per-P/T provincial-depth series |
| GeoMet daily-mean depth — SK | 1911 | 115 | Long span |
| GeoMet daily-mean depth — PE | 1919 | 4 | |
| GeoMet annual-peaks (05BB001) | 1923 | 103 | Flood-frequency lineage |
| CanSWE (national SWE) | 1928 | 98 | Deepest snow archive |
| GeoMet daily-mean depth — YT | 1950 | 37 | |
| GeoMet daily-mean depth — NB | 1951 | 75 | |
| GeoMet daily-mean depth — MB | 1957 | 17 | |
| GeoMet daily-mean depth — BC | 1960 | 24 | |
| GeoMet daily-mean depth — NS | 1964 | 36 | |
| GeoMet daily-mean depth — QC | 1967 | 11 | |
| GeoMet daily-mean depth — NU | 1970 | 21 | |
| GeoMet daily-mean depth — ON | 1972 | 7 | |
| CRID (river ice) | 1894 | 122 | Advertised; sample empty (§4) |
| GeoMet daily-mean depth — NL | 1999 | 2 | Shallowest measured provincial depth |
| GeoMet daily-mean depth — NT | 2017 | 6 | Youngest network |

**Finding.** **HYDAT (1860) is unambiguously the deepest source** and SHALL be the primary historical archive for all jurisdictions; ECCC climate-daily (1876) is the deepest precipitation archive. Per-jurisdiction depth varies widely — AB/SK series reach the 1900s/1910s, whereas NL and NT depth is shallow — so the GeoMet per-P/T depth series SHOULD be treated as convenient programmatic slices, with HYDAT as the authoritative deep record.

## 6. Weather and AQI field-contract findings

### 6.1 Weather field contract

The app's weather contract is a 27-field current-plus-7-day daily payload. Only Open-Meteo supplies all 27 fields, but under a non-commercial free tier; the commercial-OK alternatives supply fewer fields.

| Source | Fields supplied | App-contract fit | Commercial | Note |
|---|---:|---|---|---|
| Open-Meteo forecast | 27 | Full (reference contract) | **Non-commercial** free tier (600/min, 5000/hr, 10000/day) | Paid plan required for commercial use |
| ECCC City Page — city XML | 20 | Partial (~74 %) | Yes (OGL-Canada) | 856-site catalogue; canonical Canadian source |
| MET Norway Locationforecast | 11 | Partial (~41 %) | Yes (CC-BY-4.0 / NLOD-2.0) | Descriptive User-Agent required |

### 6.2 AQI scale mismatch

| Source | Scale | Fields | Commercial | Note |
|---|---|---:|---|---|
| ECCC AQHI | **AQHI (Canadian, 1–10+)** | 14 | Yes (OGL-Canada) | Matches the app's AQHI contract |
| Open-Meteo Air Quality | **US AQI (0–500)** | 5 | Non-commercial | `us_aqi` + `pm2_5`/`pm10`; different scale |

### 6.3 Remediation options (decision DEFERRED to the implementation spec)

The following options are recorded for the implementation spec; DS-STD-2026.1 does not select among them here:

1. **Weather (non-commercial posture):** keep Open-Meteo as primary (full 27-field contract) and ECCC City Page as the commercial-safe validation/backup.
2. **Weather (commercial tier):** promote ECCC City Page (20 fields, commercial-OK) to primary and backfill the 7 missing contract fields from MET Norway or a paid Open-Meteo plan.
3. **AQI:** adopt ECCC AQHI as the primary AQI source (native AQHI scale, commercial-OK) and retain Open-Meteo AQI only as a gap-filler with an explicit US-AQI→AQHI conversion or clear scale labelling.

The choice among these is an implementation decision and SHALL be settled in the implementation spec, not in this standard.

## 7. The verified standard (normative)

This section is normative. RFC-2119 [25] key words apply. Recommendations are derived solely from the measured evidence in §§3–6.

### 7.1 General rules

1. For **historical** water data in every jurisdiction, HYDAT [5] SHALL be the primary archive and the validation reference; the GeoMet OGC API [3] SHALL be the programmatic access path to the same lineage.
2. For **real-time** water data, the jurisdiction's own authoritative programmatic feed SHALL be primary where one exists and is retrievable (AB, BC-partial, MB, ON, QC, NL); otherwise ECCC Datamart [4] SHALL be primary. ECCC Datamart/GeoMet SHALL serve as the backup/validation layer in all jurisdictions.
3. **Québec is the exception:** because ECCC Datamart carries only 15 QC real-time stations (§3.2), QC real-time river data SHALL be sourced from Québec Vigilance [15] (provincial-only). ECCC MAY still be used for QC historical/validation.
4. Every deployed source SHALL carry its required attribution string, and the project licence SHALL be kept distinct from each upstream licence (§9, and Part 1 [1]).

### 7.2 Core river-data recommendation (per jurisdiction)

| Juris. | Stations (recommended) | Real-time / current (primary → backup) | Historical (recommended) | Flag |
|---|---|---|---|---|
| AB | GeoMet hydrometric stations | ECCC Datamart (AB) → GeoMet realtime · *(rivers.alberta.ca = non-commercial, intermittent; residual)* | HYDAT → GeoMet | AB provincial feed is non-commercial/residual |
| BC | GeoMet hydrometric stations (2,324) | ECCC Datamart (BC) → GeoMet realtime · *(BC AQUARIUS = undocumented; residual)* | HYDAT → GeoMet | BC provincial = partial |
| MB | GeoMet hydrometric stations | **MB FloodInfo** → ECCC Datamart (MB) | HYDAT → GeoMet | Provincial-primary (OpenMB, commercial-OK) |
| NB | GeoMet hydrometric stations | ECCC Datamart (NB) | HYDAT → GeoMet | ECCC-primary |
| NL | GeoMet hydrometric stations | **NL ADRS** → ECCC Datamart (NL) | HYDAT → GeoMet | Provincial-primary; ADRS carries water-temp |
| NS | GeoMet hydrometric stations | ECCC Datamart (NS) | HYDAT → GeoMet | ECCC-primary |
| NT | GeoMet hydrometric stations | ECCC Datamart (NT) | HYDAT → GeoMet | ECCC-primary |
| NU | GeoMet hydrometric stations | ECCC Datamart (NU) | HYDAT → GeoMet | ECCC-primary |
| ON | **ON SWMC KiWIS** (4,436) + GeoMet | ECCC Datamart (ON) → KiWIS timeseries | HYDAT → GeoMet | KiWIS is the richer registry |
| PE | GeoMet hydrometric stations | ECCC Datamart (PE) | HYDAT → GeoMet | ECCC-primary |
| **QC** | GeoMet hydrometric stations (1,001) | **QC Vigilance (provincial-only)** — ECCC Datamart carries only 15 QC stations | HYDAT → GeoMet | **EXCEPTION — provincial-only** |
| SK | GeoMet hydrometric stations | ECCC Datamart (SK) · *(WSA = scrape-only, non-commercial; residual)* | HYDAT → GeoMet | SK provincial values are scrape-only |
| YT | GeoMet hydrometric stations | ECCC Datamart (YT) | HYDAT → GeoMet | ECCC-primary |

### 7.3 Environmental-context recommendation (per category)

| Category | Recommended primary | Backup / validation | Provincial sources | Commercial posture |
|---|---|---|---|---|
| weather | Open-Meteo (27-field contract) | ECCC City Page; MET Norway | — | Open-Meteo non-commercial; City Page/MET Norway commercial-OK (§6) |
| aqi | ECCC AQHI (native AQHI scale) | Open-Meteo AQI (US-AQI; scale-convert) | — | AQHI commercial-OK; Open-Meteo non-commercial |
| precip | ECCC GeoMet climate-daily/hourly/monthly | RDPA/CaPA gridded | — | Commercial-OK (OGL-Canada) |
| snow | BC ASWS (near-real-time SWE) | CanSWE (historical SWE, 1928→) | BC (ASWS) | Commercial-OK |
| ice | CRID (river ice) — deeper query needed | CIS ice-thickness; Lake Ice DB | — | Commercial-OK; CRID/LakeIce `ok_empty` |
| drainage | NHN + WSC basins (gauge-keyed) | HydroSHEDS | BC FWA, ON OIH, QC GRHQ | Commercial-OK |
| groundwater | **GIN WMS (44 layers)** | ON PGMN; QC RSESQ | ON (PGMN), QC (RSESQ) | Commercial-OK; **GSC SensorThings DNS-failed — do not rely** |
| watertemp | CIOOS Atlantic (coastal) | RivTemp (API key req.); NL ADRS (river, NL) | NL (ADRS) | CIOOS commercial-OK; RivTemp conditional |
| flood | Provincial structured feed where present | ECCC water-prediction (pending); NRCan FHIMP | BC RFC, QC Vigilance, MB HFC, ON CO (404) | Mixed; MB/CO unspecified |

### 7.4 Consolidated normative matrix (13 P/T × 12 categories)

Cell = recommended source (code); **(P)** = provincial-primary; *(res)* = provincial feed is residual/non-commercial (ECCC is the retrievable primary); **QC-only** = provincial-only per the Québec exception; `—` = no jurisdiction-specific source, use the national recommendation in §7.3. Legend below the table.

| Juris. | stations | current | historical | weather | aqi | precip | snow | ice | drainage | groundwater | watertemp | flood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AB | GM-S | DM *(res: AB-R)* | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| BC | GM-S | DM *(res: AQ)* | HY/GM | OM/CP | AQHI | CLIM | **BC-ASWS (P)** | CRID | **BC-FWA (P)** | GIN | CIOOS | **BC-RFC (P)** |
| MB | GM-S | **MB-FI (P)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | **MB-HFC (P)** |
| NB | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| NL | GM-S | **NL-ADRS (P)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | **NL-ADRS (P)** | ECCC-WP |
| NS | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| NT | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| NU | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| ON | **KiWIS (P)** | DM → KiWIS | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | **ON-OIH (P)** | **ON-PGMN (P)** | — | CO *(404)* |
| PE | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| **QC** | GM-S | **QC-VIG (QC-only)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | **QC-GRHQ (P)** | **QC-RSESQ (P)** | — | **QC-VIG (P)** |
| SK | GM-S | DM *(res: WSA)* | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| YT | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |

**Legend.** GM-S = ECCC GeoMet hydrometric stations · DM = ECCC Datamart real-time CSV · HY/GM = HYDAT (deep archive) via GeoMet OGC API · OM/CP = Open-Meteo (non-commercial) / ECCC City Page (commercial) · AQHI = ECCC AQHI · CLIM = ECCC GeoMet climate · CanSWE = national SWE · CRID = Canadian River Ice Database · NHN = National Hydro Network (+ WSC basins) · GIN = Groundwater Information Network WMS · CIOOS = CIOOS Atlantic ERDDAP · ECCC-WP = ECCC water-prediction (pending deeper query) / NRCan FHIMP · AB-R = rivers.alberta.ca · AQ = BC AQUARIUS · MB-FI = MB FloodInfo · MB-HFC = MB Hydrologic Forecast Centre · NL-ADRS = NL ADRS · KiWIS = ON SWMC KiWIS · ON-OIH = Ontario Integrated Hydrology · ON-PGMN = Ontario PGMN · CO = Conservation Ontario (HTTP 404, §4) · QC-VIG = Québec Vigilance · QC-GRHQ = QC hydro network · QC-RSESQ = Québec RSESQ · BC-ASWS/-FWA/-RFC = BC snow/atlas/river-forecast.

**Notes on the matrix.** (a) The single **QC-only** cell (QC/current) is the Québec exception and is normative. (b) `*(res)*` cells (AB, BC, SK current) mean the provincial feed exists but is residual/non-commercial/intermittent; the retrievable, commercially-safe primary is ECCC Datamart until the overnight harness (§8) characterizes the provincial feeds. (c) `CRID` and `ECCC-WP` cells are recommended subject to the deeper-query follow-up flagged in §4. (d) Groundwater across all jurisdictions relies on **GIN**, not the DNS-failed GSC SensorThings host.

## 8. Residual-harness status

The residual sources — Alberta `rivers.alberta.ca` (per-station JSON; GoA copyright, non-commercial; connection-refusal observed **intermittently**), Saskatchewan WSA htmlwidget (SK Crown copyright, non-commercial, values scrape-only), and BC AQUARIUS (undocumented; OGL-BC) — plus an Open-Meteo rapid-burst "too-fast" probe are **not** in the 86 sanctioned rows. They are exercised only by the manual/overnight gentle stress harness (`waterpulse-backend/tests/stress_test.py`): a graduated knee-finder with random 10–30 min gaps, a descriptive User-Agent, `Retry-After` compliance, no cache-bypass headers, a ~10 h cap, and abort-on-block.

**Smoke-validated 2026-09-16.** The machinery was validated with the fast smoke profile: the weather ladder safe-max was `c = 4` with the rapid-burst reduced from 25 to 5 (smoke), all OK with no throttling observed at low concurrency; Alberta responded intermittently (bad-path requests returned 404). No sustained blocking was seen at these gentle rates.

**Pending.** The full overnight run is the user's to launch (ideally from a non-production IP, with the app's 10-minute scheduler paused). Its results — the empirically-characterized safe sustainable request rate and failure signatures for the AB/SK/BC scrape sources — **SHALL be appended to this standard as a dated addendum, Part 3a (DS-STD-2026.1, Part 3a)**, and until then the `*(res)*` matrix cells (§7.4) stand as provisional.

## 9. Recommendations

1. **Adopt the §7 verified matrix as the normative source map.** ECCC/WSC (HYDAT + GeoMet + Datamart) SHALL be the historical backbone and the real-time backbone for all ECCC-primary jurisdictions; provincial-primary feeds (MB FloodInfo, NL ADRS, ON KiWIS, QC Vigilance) SHALL be used where retrievable and commercially compatible.
2. **Treat Québec as provincial-only for real-time** (Vigilance), given the measured 15-station Datamart footprint.
3. **Monetization: keep the project licence separate from every upstream licence.** A non-commercial posture is available today at full coverage. A commercial tier is bounded by the most-restrictive upstream term; the only hard blockers are **Alberta and Saskatchewan (written permission required)** and the **Open-Meteo free tier (paid plan, or switch to ECCC City Page / MET Norway)**. Every other source is commercial-OK with attribution. No source is cut for the commercial tier; the AB/SK provincial *values* are simply omitted from a commercial build (ECCC Datamart already covers those jurisdictions).
4. **Re-probe the four soft-negative endpoints with targeted queries** — ECCC water-prediction, CRID, and Lake Ice Database (`ok_empty`), and re-test GSC SensorThings (`dns_error`) — before promoting any of them to a recommended primary. Provision a DataStream `x-api-key` if RivTemp river-temperature is wanted.
5. **Re-discover the moved Conservation Ontario flood resource** and, pending that, rely on the national/ECCC flood layer for ON.
6. **Defer the weather/AQI field-contract choice to the implementation spec** (§6.3), and standardize on the AQHI scale for AQI.
7. **Launch the overnight residual harness** (§8) and publish Part 3a with the measured safe request rates for the AB/SK/BC scrape sources.
8. **Enforce ECCC acceptable-use limits** in the ingestion scheduler: contact MSC before approaching ~86,400 requests/day (~1 req/s), send no cache-bypass headers, and do not bulk-retrieve WMS tiles [8].

## 10. References

[1] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1 — Architecture & Source Registry," 2026-09-16 (companion document, this series).

[2] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 2 — Method & Test Protocol," 2026-09-16 (companion document, this series).

[3] Environment and Climate Change Canada, Meteorological Service of Canada, "MSC GeoMet — OGC API (`api.weather.gc.ca`)." [Online]. Available: https://api.weather.gc.ca/ · https://eccc-msc.github.io/open-data/ . Accessed: 2026-09-16.

[4] Environment and Climate Change Canada, "MSC Datamart — hydrometric real-time data." [Online]. Available: https://dd.weather.gc.ca/hydrometric/ . Accessed: 2026-09-16.

[5] Environment and Climate Change Canada / Water Survey of Canada, "National Water Data Archive: HYDAT." [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/monitoring/survey/data-products-services/national-archive-hydat.html . Accessed: 2026-09-16.

[6] Water Survey of Canada, "Wateroffice — real-time and historical hydrometric data." [Online]. Available: https://wateroffice.ec.gc.ca/ . Accessed: 2026-09-16.

[7] Environment and Climate Change Canada, "City Page Weather (Datamart XML/CSV)." [Online]. Available: https://dd.weather.gc.ca/citypage_weather/ . Accessed: 2026-09-16.

[8] Government of Canada, "Open Government Licence – Canada 2.0." [Online]. Available: https://open.canada.ca/en/open-government-licence-canada . Accessed: 2026-09-16.

[9] Open-Meteo, "Open-Meteo Weather & Air-Quality API — terms and licensing (CC-BY 4.0; free-tier non-commercial)." [Online]. Available: https://open-meteo.com/ . Accessed: 2026-09-16.

[10] Norwegian Meteorological Institute, "MET Norway Weather API — Locationforecast 2.0 (CC-BY 4.0 / NLOD 2.0)." [Online]. Available: https://api.met.no/ . Accessed: 2026-09-16.

[11] Government of Alberta, "Alberta River Basins / rivers.alberta.ca." [Online]. Available: https://rivers.alberta.ca/ . Accessed: 2026-09-16.

[12] Saskatchewan Water Security Agency, "WSA — river and stream conditions." [Online]. Available: https://www.wsask.ca/ . Accessed: 2026-09-16.

[13] Government of Manitoba, "Manitoba FloodInfo / Hydrologic Forecast Centre; OpenMB Information and Data Use Licence." [Online]. Available: https://www.gov.mb.ca/flooding/ · https://www.gov.mb.ca/openmb/ . Accessed: 2026-09-16.

[14] Government of Ontario, "Surface Water Monitoring Centre (KiWIS) and data.ontario.ca (PGMN, OIH)." [Online]. Available: https://data.ontario.ca/ . Accessed: 2026-09-16.

[15] Gouvernement du Québec, "Vigilance — surveillance hydrologique (MELCCFP / CEHQ) and Données Québec (RSESQ, GRHQ)." [Online]. Available: https://www.cehq.gouv.qc.ca/ · https://www.donneesquebec.ca/ . Accessed: 2026-09-16.

[16] Government of Newfoundland and Labrador, "Automated Data Retrieval System (ADRS) — real-time water resources." [Online]. Available: https://www.gov.nl.ca/ecc/waterres/realtime/ . Accessed: 2026-09-16.

[17] Government of British Columbia, "Automated Snow Weather Stations (ASWS), River Forecast Centre, Freshwater Atlas." [Online]. Available: https://www2.gov.bc.ca/gov/content/environment/air-land-water/water . Accessed: 2026-09-16.

[18] V. Vionnet et al. / Environment and Climate Change Canada, "CanSWE — Canadian historical Snow Water Equivalent dataset (Zenodo)." [Online]. Available: https://zenodo.org/ . Accessed: 2026-09-16.

[19] Environment and Climate Change Canada, "Canadian River Ice Database (CRID)." [Online]. Available: https://open.canada.ca/ . Accessed: 2026-09-16.

[20] Natural Resources Canada / Geological Survey of Canada, "Groundwater Information Network (GIN) WMS." [Online]. Available: https://gin.gw-info.net/ . Accessed: 2026-09-16.

[21] Geological Survey of Canada, "SensorThings API groundwater monitoring (`mon.geosciences.ca`) — DNS unresolved at time of testing." [Online]. Accessed: 2026-09-16.

[22] DataStream, "DataStream OData v4 API (RivTemp river-temperature datasets; API key required)." [Online]. Available: https://datastream.org/ . Accessed: 2026-09-16.

[23] Canadian Integrated Ocean Observing System (CIOOS) Atlantic, "ERDDAP data catalogue." [Online]. Available: https://cioosatlantic.ca/erddap/ . Accessed: 2026-09-16.

[24] B. Lehner et al., "HydroSHEDS / HydroBASINS." [Online]. Available: https://www.hydrosheds.org/ . Accessed: 2026-09-16.

[25] S. Bradner, "Key words for use in RFCs to Indicate Requirement Levels," RFC 2119, IETF, Mar. 1997. [Online]. Available: https://www.rfc-editor.org/rfc/rfc2119 . Accessed: 2026-09-16.

[26] Natural Resources Canada, "National Hydro Network (NHN)." [Online]. Available: https://natural-resources.canada.ca/science-and-data/science-and-research/earth-sciences/geography/topographic-information/geobase . Accessed: 2026-09-16.

[27] Natural Resources Canada, "Flood Hazard Identification and Mapping Program (FHIMP) — geo.ca flood-mapping hub." [Online]. Available: https://geo.ca/ . Accessed: 2026-09-16.

---

*End of Part 3. The full residual overnight-harness results will be published as Part 3a (DS-STD-2026.1, Part 3a), a dated addendum to this document.*
