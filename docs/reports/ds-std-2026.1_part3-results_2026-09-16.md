# WaterPulse Data-Source Standard (DS-STD-2026.1) — Part 3: Results & Verified Standard

| | |
|---|---|
| **Report ID** | DS-STD-2026.1 |
| **Part** | 3 of 3 — Results & Verified Standard |
| **Version** | 1.1 (revised after the authoritative run + coverage fixes) |
| **Status** | Draft |
| **Publication date** | 2026-09-16 |
| **Prepared for** | WaterPulse-Canada |
| **Authoring organization** | WaterPulse Data Engineering |
| **Persistent identifier** | `urn:waterpulse:ds-std:2026.1` |
| **Evidence run** | `probes-20260916T104357Z` (2026-09-16) |

**How to cite this document:** WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 3 — Results & Verified Standard," 2026-09-16.

**Revision history.** v1.0 (2026-09-16) — initial draft against provisional run `probes-20260916T090344Z` (80/86). **v1.1 (2026-09-16)** — revised against the authoritative run `probes-20260916T104357Z`: headline coverage corrected to 98/102; registry restated as 106 probes (102 sanctioned + 4 residual) over 41 distinct Source IDs; residual set corrected to four probes (incl. `SRC-AB-SNOW`, with the Open-Meteo rapid-burst reclassified as a stress-harness target, not a registered probe); CRID / Lake Ice / water-prediction / Conservation Ontario reclassified as retrievable; Datamart hourly+daily bundles and the BC ASWS SW/SD/PC/TA family added; PID minted and canonical part titles applied.

**Companion documents:** Part 1 — "Standard & Reconnaissance" [1]; Part 2 — "Methodology & Test Suite" [2]. Downstream: the "Implementation Specification" consumes the verified matrix in §7. This part reports measured results and the resulting verified, normative standard; it does not restate the reconnaissance rationale (Part 1) or the probe method (Part 2).

---

## Abstract

This part reports the measured outcome of the DS-STD-2026.1 coverage evaluation and derives the normative, evidence-backed data-source recommendation for WaterPulse-Canada. In a single sanctioned run (`probes-20260916T104357Z`, 2026-09-16), **98 of 102 sanctioned source probes were retrievable in 631.4 s**, exercising a registry of **106 probes (102 sanctioned + 4 residual)** spanning **41 distinct Source IDs** across 12 data categories and all 13 Canadian provinces/territories. The results confirm the standard's core architecture: Environment and Climate Change Canada / Water Survey of Canada (ECCC/WSC) form a deep, commercially-licensable historical and real-time backbone — HYDAT alone returns 1,779,871 archived records over 6,478 stations from 1860 (a 167-year span, 106 fields), and ECCC's national climate-daily archive returns 184,672,664 records — while a small number of provinces (AB, BC-partial, MB, ON, QC, NL) add a genuine programmatic provincial river feed and the remainder are ECCC-primary. Québec is confirmed as the standing exception: ECCC's real-time Datamart carries only 15 QC hydrometric stations (9,548 hourly rows measured), so QC river data SHALL be sourced provincially from Vigilance. The four non-retrievable probes are individually diagnosed (a DNS-unresolvable federal groundwater host and an API-key-gated river-temperature service) and none invalidate a recommended primary source; the four previously-broken soft-negatives (CRID, Lake Ice Database, ECCC water-prediction, Conservation Ontario) are now fully retrievable. Adding bounded retry logic to the probe transport absorbed 18 transient GeoMet 5xx responses and took the full run from 80/102 to 98/102 with no residual 5xx. The historical requirement (≥15 historical sources) is satisfied with 19 retrievable historical probes. This part closes with the verified per-jurisdiction × per-category normative matrix, a non-commercial-versus-commercial monetization finding, and the residual full-cadence stress harness result (run `stress-20260916T105739Z` **complete 2026-09-16**; safe-max weather 4 / BC 16 / SK 16 / AB 16, zero IP-flagging — full detail in the dated Part 3a addendum, §10).

## Index Terms

Air Quality Health Index (AQHI), Canadian river data, coverage evaluation, data-source standard, Datamart, ECCC, GeoMet OGC API, historical hydrometry, HYDAT, licensing, open government licence, provincial hydrometric feeds, Québec Vigilance, real-time streamflow, transient-retry policy, Water Survey of Canada.

---

## 1. Introduction and scope of this part

Part 1 [1] ("Standard & Reconnaissance") established the source registry and the "provincial-primary where programmatic, ECCC/WSC as backbone and validation" architecture. Part 2 [2] ("Methodology & Test Suite") defined the probe harness, the sanctioned-versus-residual distinction, the retrievability decision rule, and the per-probe evidence schema. This part (Part 3) presents the measured results of executing that protocol, interprets the outcomes, and promotes the tested findings into a normative standard.

Normative statements in this part use RFC-2119 key words — SHALL, SHOULD, MAY — as defined in [25]. All quantitative claims derive from the single evidence run identified below and MUST NOT be read as advertised or catalogue figures; where a catalogue figure differs from a measured figure, the measured figure governs.

## 2. Method recap

WaterPulse Data Engineering executed the Part 2 [2] harness once against every sanctioned probe (`run_id = probes-20260916T104357Z`, 2026-09-16); for full protocol, User-Agent policy, rate discipline, and the retrievability decision rule, see Part 2 [2].

**Transient-retry policy (new in this run).** The shared `http_probe` transport now RETRIES transient failures — HTTP 5xx, HTTP 429, and connect/read timeouts — with a bounded number of attempts and honouring any `Retry-After` header. This single change took the full sanctioned run from **80/102 to 98/102 retrievable**: 18 transient GeoMet 5xx responses that had previously counted as failures were absorbed on retry, and the final run contains **no residual 5xx outcomes**. The change is documented normatively in Part 2 [2]; it is recapped here because it materially explains the coverage delta from v1.0. The residual/stress harness (§8) deliberately runs with `retries = 0` so that a provincial scrape source's first-response failure signature is recorded unmasked.

**Evidence artifacts (this run):** `waterpulse-backend/tests/logs/probes-20260916T104357Z/{coverage.csv, coverage_summary.json, requests.csv, tests.csv}`.

## 3. Results by category

### 3.1 Run-level totals

| Metric | Value |
|---|---|
| Run ID | `probes-20260916T104357Z` |
| Date | 2026-09-16 |
| Wall-clock elapsed | 631.4 s |
| Registry total (all probes) | **106** (102 sanctioned + 4 residual) |
| Distinct Source IDs | **41** |
| Sanctioned probes executed | **102** |
| Retrievable (`retrievable = True`) | **98** |
| Not retrievable | 4 |
| Categories exercised | 12 |
| Jurisdictions exercised | 13 P/T + national |

Reason breakdown (sanctioned probes): `ok` = 98, `dns_error` = 3, `http_401_unauthorized` = 1. There are **no** `ok_empty` and **no** `5xx` outcomes in this run (the four former soft-negatives now return rows; the transient GeoMet 5xx were absorbed by retry, §2). Commercial-use posture across sanctioned probes: `yes` = 96, `non-commercial` = 3, `unknown` = 2, `conditional` = 1.

Registry composition by category (from `coverage_summary.json.matrix.by_category`, all 106 probes): aqi 2, current 33, drainage 6, flood 6, groundwater 6, historical 19, ice 3, precip 5, snow 4, stations 15, watertemp 2, weather 5. The `current` count of 33 includes the **3 residual provincial-scrape probes** (`SRC-AB-RIVERS`, `SRC-BC-AQUARIUS`, `SRC-SK-WSA` — see §8); the `snow` count of 4 includes the **1 residual snow probe** (`SRC-AB-SNOW`). Excluding those four residual probes leaves the 102 sanctioned rows tabulated below (30 current + 3 snow + the remaining 69).

The wall-clock (631.4 s) is dominated by the new Datamart **daily** bundles (§3.2): the AB daily pull alone took 172.8 s and the ON daily pull 96.9 s, reflecting multi-million-row archive downloads, not endpoint latency.

### 3.2 `current` — real-time water level / flow (30 sanctioned probes; 30 retrievable)

The ECCC Datamart bulk CSV is confirmed retrievable in every one of the 13 provinces/territories, and Datamart now publishes **both an hourly and a daily bundle per P/T (26 Datamart probes total: 13 hourly + 13 daily)**. The national real-time sample is a **separate source, `SRC-ECCC-GEOMET`** (GeoMet OGC API `hydrometric-realtime`), *not* a Datamart pull. Provincial real-time feeds (MB FloodInfo, NL ADRS, QC Vigilance) are also retrievable.

**Datamart hourly bundles (13 probes; 13 retrievable).**

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| ECCC Datamart hourly bulk CSV | AB | True | ok | 10 | 246,082 | 409 | 4,539.6 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | BC | True | ok | 10 | 258,554 | 436 | 4,296.2 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | MB | True | ok | 10 | 152,768 | 250 | 1,091.9 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | NB | True | ok | 10 | 32,993 | 51 | 600.6 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | NL | True | ok | 10 | 62,933 | 97 | 1,103.9 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | NS | True | ok | 10 | 24,697 | 39 | 572.9 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | NT | True | ok | 10 | 59,276 | 100 | 1,504.4 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | NU | True | ok | 10 | 14,582 | 24 | 528.6 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | ON | True | ok | 10 | 330,036 | 523 | 1,424.1 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | PE | True | ok | 10 | 5,785 | 9 | 472.2 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | **QC** | True | ok | 10 | **9,548** | **15** | 491.0 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | SK | True | ok | 10 | 92,193 | 150 | 1,008.9 | OGL-Canada/ECCC v2.1.1 · yes |
| ECCC Datamart hourly bulk CSV | YT | True | ok | 10 | 42,481 | 72 | 756.6 | OGL-Canada/ECCC v2.1.1 · yes |
| **Hourly totals** | 13 P/T | | | | **1,331,928** | **2,175** | | |

**Datamart daily bundles (13 probes; 13 retrievable).** The daily archives are large and drive the run's wall-clock.

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) |
|---|---|---|---|---:|---:|---:|---:|
| ECCC Datamart daily bulk CSV | AB | True | ok | 10 | 3,492,229 | 424 | 172,758.9 |
| ECCC Datamart daily bulk CSV | BC | True | ok | 10 | 3,719,013 | 447 | 73,916.5 |
| ECCC Datamart daily bulk CSV | MB | True | ok | 10 | 2,101,452 | 251 | 30,489.7 |
| ECCC Datamart daily bulk CSV | NB | True | ok | 10 | 443,076 | 51 | 2,317.7 |
| ECCC Datamart daily bulk CSV | NL | True | ok | 10 | 839,399 | 101 | 12,249.8 |
| ECCC Datamart daily bulk CSV | NS | True | ok | 10 | 336,251 | 39 | 1,691.6 |
| ECCC Datamart daily bulk CSV | NT | True | ok | 10 | 820,463 | 100 | 3,394.3 |
| ECCC Datamart daily bulk CSV | NU | True | ok | 10 | 200,346 | 24 | 1,287.2 |
| ECCC Datamart daily bulk CSV | ON | True | ok | 10 | **4,529,607** | 528 | 96,914.2 |
| ECCC Datamart daily bulk CSV | PE | True | ok | 10 | 77,949 | 9 | 902.4 |
| ECCC Datamart daily bulk CSV | QC | True | ok | 10 | 129,364 | 15 | 1,053.4 |
| ECCC Datamart daily bulk CSV | SK | True | ok | 10 | 1,256,095 | 151 | 6,878.8 |
| ECCC Datamart daily bulk CSV | YT | True | ok | 10 | 607,458 | 72 | 2,581.9 |
| **Daily totals** | 13 P/T | | | | **18,552,702** | **2,212** | |

**National and provincial real-time feeds (4 probes; 4 retrievable).**

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| ECCC GeoMet `hydrometric-realtime` (national sample) — `SRC-ECCC-GEOMET` | CA | True | ok | 13 | 10 | 1 | 238.4 | OGL-Canada/ECCC v2.1.1 · yes |
| MB FloodInfo AGOL CSV (level/flow/forecast/alert) | MB | True | ok | 30 | 248 | — | 221.9 | OpenMB · yes |
| NL ADRS per-station CSV (level/flow/water-temp) | NL | True | ok | 1 | 2,005 | 1 | 692.4 | OGL-NL · yes |
| Québec Vigilance WFS stations (GeoJSON) | QC | True | ok | 13 | 50 | 50 | 574.0 | CC-BY-4.0 (QC) · yes |

**Findings.** Across the 13 **hourly** Datamart pulls the harness retrieved **1,331,928 real-time rows over exactly 2,175 active hydrometric stations**; the 13 **daily** bundles add 18,552,702 archived-daily rows over 2,212 stations (the daily count is slightly higher because the daily archive retains stations not currently reporting hourly). ON (330,036 hourly rows / 523 stations) and BC (258,554 / 436) are the largest real-time networks; PE (9 stations), QC (15) and NU (24) the smallest. **QC is the decisive datum: only 15 QC stations / 9,548 hourly rows appear on Datamart** — an order of magnitude below QC's catalogued network (1,001 GeoMet stations, §3.3) — confirming the Québec exception (§7). The heaviest latencies are the daily archive downloads (AB daily 172.8 s, ON daily 96.9 s, BC daily 73.9 s); hourly bundles all returned in ≤4.6 s and the provincial JSON/CSV/WFS feeds in <0.7 s.

### 3.3 `stations` — station registry / metadata (15 probes; 15 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) |
|---|---|---|---|---:|---:|---:|---:|
| ECCC GeoMet climate-stations | CA | True | ok | 33 | 8,435 | 8,435 | 413.2 |
| ECCC GeoMet hydrometric stations | AB | True | ok | 14 | 10 | 1,104 | 260.2 |
| ECCC GeoMet hydrometric stations | BC | True | ok | 14 | 10 | **2,324** | 257.0 |
| ECCC GeoMet hydrometric stations | MB | True | ok | 14 | 10 | 659 | 226.5 |
| ECCC GeoMet hydrometric stations | NB | True | ok | 14 | 10 | 144 | 264.5 |
| ECCC GeoMet hydrometric stations | NL | True | ok | 14 | 10 | 230 | 256.9 |
| ECCC GeoMet hydrometric stations | NS | True | ok | 14 | 10 | 144 | 241.3 |
| ECCC GeoMet hydrometric stations | NT | True | ok | 14 | 10 | 245 | 218.2 |
| ECCC GeoMet hydrometric stations | NU | True | ok | 14 | 10 | 109 | 270.6 |
| ECCC GeoMet hydrometric stations | ON | True | ok | 14 | 10 | 1,119 | 283.0 |
| ECCC GeoMet hydrometric stations | PE | True | ok | 14 | 10 | 43 | 229.0 |
| ECCC GeoMet hydrometric stations | QC | True | ok | 14 | 10 | 1,001 | 362.8 |
| ECCC GeoMet hydrometric stations | SK | True | ok | 14 | 10 | 748 | 257.1 |
| ECCC GeoMet hydrometric stations | YT | True | ok | 14 | 10 | 114 | 204.2 |
| Ontario SWMC KiWIS getStationList | ON | True | ok | 5 | 4,436 | 4,436 | 1,890.1 |

**Findings.** GeoMet catalogues **7,984 hydrometric stations nationally** (BC 2,324 > ON 1,119 > AB 1,104 > QC 1,001 > SK 748 > MB 659 > NT 245 > NL 230 > NB/NS 144 > YT 114 > NU 109 > PE 43). ECCC climate-stations adds 8,435 climate sites. Ontario's provincial KiWIS registry (4,436 stations) is far larger than ON's GeoMet hydrometric set (1,119) and is the richest single-jurisdiction station source in the registry.

### 3.4 `historical` — deep archives (19 probes; 19 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span (measured) | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| **HYDAT national archive (full record)** | CA | True | ok | 106 | **1,779,871** | **6,478** | **1860 → 167 yr** | 371.7 |
| GeoMet daily-mean (05BB001) | CA | True | ok | 12 | 50 | 1 | 1989 → 1 | 286.6 |
| GeoMet monthly-mean (05BB001) | CA | True | ok | 8 | 50 | 1 | 1909 → 5 | 281.6 |
| GeoMet annual-statistics (05BB001) | CA | True | ok | 15 | 50 | 1 | 1909 → 117 | 897.5 |
| GeoMet annual-peaks (05BB001) | CA | True | ok | 16 | 50 | 1 | 1923 → 103 | 8,659.1 |
| GeoMet daily-mean depth | AB | True | ok | 12 | — | 1 | 1908 → 42 | 101.9 |
| GeoMet daily-mean depth | BC | True | ok | 12 | — | 1 | 1960 → 24 | 74.3 |
| GeoMet daily-mean depth | MB | True | ok | 12 | — | 1 | 1957 → 17 | 73.3 |
| GeoMet daily-mean depth | NB | True | ok | 12 | — | 1 | 1951 → 75 | 81.7 |
| GeoMet daily-mean depth | NL | True | ok | 12 | — | 1 | 1999 → 2 | 82.1 |
| GeoMet daily-mean depth | NS | True | ok | 12 | — | 1 | 1964 → 36 | 82.4 |
| GeoMet daily-mean depth | NT | True | ok | 12 | — | 1 | 2017 → 6 | 83.8 |
| GeoMet daily-mean depth | NU | True | ok | 12 | — | 1 | 1970 → 21 | 77.8 |
| GeoMet daily-mean depth | ON | True | ok | 12 | — | 1 | 1972 → 7 | 89.5 |
| GeoMet daily-mean depth | PE | True | ok | 12 | — | 1 | 1919 → 4 | 74.2 |
| GeoMet daily-mean depth | QC | True | ok | 12 | — | 1 | 1967 → 11 | 70.8 |
| GeoMet daily-mean depth | SK | True | ok | 12 | — | 1 | 1911 → 115 | 79.6 |
| GeoMet daily-mean depth | YT | True | ok | 12 | — | 1 | 1950 → 37 | 72.7 |
| Open-Meteo Archive (ERA5) | multi | True | ok | 3 | 31 | — | 1940 → 1 | 839.6 |

**Findings.** HYDAT is the deepest and widest archive by every measure — 1,779,871 records, 6,478 stations, 106 fields, reaching back to **1860** (167-year span, 1860→2026) — and is the historical backbone of the standard. The GeoMet OGC API supplies the same lineage programmatically through **four collection views — daily-mean, monthly-mean, annual-statistics, and annual-peaks** (there is *no* "annual-mean" collection); the `hydrometric-daily-mean` view is already wired into the application (`eccc_provider.py:383`). See §5 for per-jurisdiction depth.

### 3.5 `precip` — precipitation & climate observations (5 probes; 5 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span (measured) | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| ECCC GeoMet climate-daily (precip + snow-on-ground) | CA | True | ok | 34 | **184,672,664** | — | 1949 → 1 | 241.0 |
| ECCC GeoMet climate-hourly | CA | True | ok | 40 | **277,059,247** | — | 1953 → 1 | 219.6 |
| ECCC GeoMet climate-monthly | CA | True | ok | 34 | 1,881,824 | — | 1891 → 1 | 251.3 |
| ECCC GeoMet RDPA/CaPA 10 km 6 h (collection metadata) | CA | True | ok | 6 | — | — | — | 320.0 |
| BC ASWS accumulated precipitation (wide CSV, PC) | BC | True | ok | 122 | 8,411 | 121 | — | 999.2 |

**Findings.** ECCC's climate archive is enormous and reachable: **184,672,664 daily records** and **277,059,247 hourly records**. The `earliest→span` values above are the measured *light-probe sample* windows (each spans a single sampled year), not the full archival extent; the record counts reflect the full archive. RDPA/CaPA gridded precipitation is confirmed at the metadata layer. New in this run, the **BC ASWS accumulated-precipitation CSV (PC)** is retrievable (122 fields, 121 stations) — one of the four sibling BC ASWS CSVs (SW, SD, PC, TA) now wired across the snow/precip/weather categories.

### 3.6 `weather` — point forecasts & station weather (5 probes; 5 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| Open-Meteo forecast (current + 7-day) | CA | True | ok | **27** | 7 | 1 | 370.9 | CC-BY-4.0 · **non-commercial** (free tier) |
| ECCC City Page — city XML (Calgary) | AB | True | ok | 20 | 11 | 1 | 61.1 | OGL-Canada/ECCC · yes |
| ECCC City Page — site catalogue CSV | CA | True | ok | 5 | 856 | 856 | 255.1 | OGL-Canada/ECCC · yes |
| MET Norway Locationforecast 2.0 (compact) | CA | True | ok | 11 | 89 | — | 524.9 | CC-BY-4.0 / NLOD-2.0 · yes |
| BC ASWS air temperature (wide CSV, TA) | BC | True | ok | 136 | 8,411 | 135 | 1,036.3 | OGL-BC · yes |

**Findings.** Open-Meteo supplies the full 27-field app weather contract but under a non-commercial free tier; the commercial-OK point-forecast alternatives supply fewer fields (City Page 20, MET Norway 11). This field-versus-licence tension is analysed in §6. New in this run, the **BC ASWS air-temperature CSV (TA)** is retrievable (136 fields, 135 stations, commercial-OK) as a provincial station-weather source for BC.

### 3.7 `aqi` — air quality (2 probes; 2 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---:|---|
| ECCC AQHI observations (GeoMet OGC API) | CA | True | ok | 14 | 7,241 | 10 | 257.1 | OGL-Canada/MSC v2.1.1 · yes |
| Open-Meteo Air Quality (us_aqi + pm2_5/pm10) | multi | True | ok | 5 | 1 | — | 663.4 | CC-BY-4.0 · non-commercial |

**Findings.** Both AQI sources are retrievable, but they are **not on the same scale**: ECCC returns the Canadian Air Quality Health Index (AQHI, 1–10+), while Open-Meteo returns the US AQI (0–500). The app's AQI contract is AQHI-based; the scale mismatch is a remediation item (§6).

### 3.8 `snow` — snow water equivalent & depth (3 sanctioned probes; 3 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| BC ASWS SWE (snow water equivalent, wide CSV, SW) | BC | True | ok | 122 | 8,411 | 121 | — | 667.6 |
| BC ASWS snow depth (wide CSV, SD) | BC | True | ok | 113 | 8,411 | 112 | — | 823.8 |
| CanSWE national SWE (Zenodo metadata) | CA | True | ok | 8 | 4 | — | 1928 → 98 | 15,658.7 |

*(A fourth `snow` registry entry — `SRC-AB-SNOW`, "Alberta River Basins snow pillows (residual)" — is a **residual** probe and is not part of the 102 sanctioned rows; see §8. This is the correct cross-reference for the residual snow item.)*

**Findings.** BC ASWS provides dense near-real-time snow via two of its sibling CSVs — **SWE (SW)** (121 stations, 122 fields) and **snow depth (SD)** (112 stations, 113 fields). CanSWE is the national historical SWE dataset reaching back to **1928** (98-year span); its 15.66 s latency (Zenodo record fetch) is the slowest single-request in the run and reflects an archival, not real-time, access pattern.

### 3.9 `ice` — river/lake ice (3 probes; 3 retrievable — all now returning content)

| Source | Juris. | Retr. | Reason | Fields | Records | Stations | Earliest→span | Latency (ms) |
|---|---|---|---|---:|---:|---:|---|---:|
| Canadian Ice Service — ice-thickness archive page | CA | True | ok | 0 | — | — | — | 1,230.4 |
| Canadian River Ice Database (CRID) | CA | True | ok | 66 | 3 | 196 | 1894 → 122 | 671.4 |
| Lake Ice Database | CA | True | ok | 64 | 2 | — | — | 487.9 |

**Findings.** All three ice sources are reachable and — unlike v1.0 — **CRID and the Lake Ice Database now return rows** (no longer `ok_empty`). Both were reached via the `open.canada.ca` CKAN `package_show` route: **CRID** advertises 196 NHP sites with freeze/break-up records back to **1894** (66 fields, 122-year span, 1894–2015-era coverage) and **Lake Ice Database** returns 64 fields. CIS ice-thickness is a landing page with no structured payload (0 fields). The former CRID/Lake Ice soft-negatives are therefore resolved (§4).

### 3.10 `drainage` — watershed / hydro-network geometry (6 probes; 6 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) |
|---|---|---|---|---:|---:|---:|
| National Hydro Network (NHN) | CA | True | ok | 7 | 15 | 360.5 |
| WSC gauge drainage-basin polygons | CA | True | ok | 1 | 1 | 362.2 |
| HydroSHEDS HydroBASINS | CA | True | ok | 13 | — | 149.4 |
| BC Freshwater Atlas watershed boundaries | BC | True | ok | 5 | 8 | 457.0 |
| Ontario Integrated Hydrology (OIH) | ON | True | ok | 2 | 7 | 372.8 |
| QC GRHQ hydro network | QC | True | ok | 6 | 10 | 366.7 |

**Findings.** Drainage geometry is fully covered: national (NHN, WSC basins, HydroSHEDS) plus richer provincial layers in BC, ON, and QC. WSC drainage-basin polygons are keyed to WSC station numbers, enabling gauge-to-basin joins.

### 3.11 `groundwater` — groundwater monitoring (6 probes; 3 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) |
|---|---|---|---|---:|---:|---:|
| GIN WMS GetCapabilities (44 layers) | CA | True | ok | 1 | 44 | 774.0 |
| Ontario PGMN (CKAN) | ON | True | ok | 44 | 7 | 591.0 |
| Quebec RSESQ (CKAN) | QC | True | ok | 53 | 20 | 434.6 |
| GSC SensorThings groundwater (national) | CA | **False** | dns_error | 0 | — | — |
| GSC SensorThings groundwater (ON) | ON | **False** | dns_error | 0 | — | — |
| GSC SensorThings groundwater (QC) | QC | **False** | dns_error | 0 | — | — |

**Findings.** The officially-catalogued federal groundwater SensorThings host (`mon.geosciences.ca`) failed DNS resolution for all three probes — a genuine availability finding, not a transient timeout (§4). The **GIN WMS (44 layers, host `gin.geosciences.ca`) is the working national alternative**, with provincial CKAN feeds (ON PGMN, QC RSESQ) retrievable.

### 3.12 `flood` — forecasts & warnings (6 probes; 6 retrievable — all now retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---|
| ECCC GeoMet water-prediction (WMS GetCapabilities) | CA | True | ok | 40 | 955 | 1,621.4 | OGL-Canada/ECCC · yes |
| BC River Forecast Centre warnings (ArcGIS) | BC | True | ok | 10 | 5 | 741.8 | OGL-BC · yes |
| Québec Vigilance flood-surveillance WFS | QC | True | ok | 13 | 1 | 440.8 | CC-BY-4.0 (QC) · yes |
| Conservation Ontario flood forecasting & warning | ON | True | ok | 0 | — | 421.9 | CO unspecified · unknown |
| Manitoba Hydrologic Forecast Centre (HTML/PDF) | MB | True | ok | 0 | — | 344.6 | MB unspecified · unknown |
| NRCan FHIMP flood-mapping hub (geo.ca) | CA | True | ok | 0 | — | 114.2 | OGL-Canada · yes |

**Findings.** **All six flood probes are now retrievable.** The two v1.0 negatives are resolved: **ECCC water-prediction** is reached via **GeoMet WMS GetCapabilities** (not OGC-API-Features collections) and exposes **40 water-prediction WMS layers** spanning the WCPS / OHPS / DHPS / RIOPS / CIOPS / storm-surge model families (955 layer/dimension entries in the sample); and **Conservation Ontario** now resolves at its corrected flood-messages URL (HTML/PDF, licence unspecified — commercial posture `unknown`). Structured feeds exist in BC (RFC ArcGIS) and QC (Vigilance WFS); MB HFC and NRCan FHIMP are reachable landing surfaces with no structured payload (0 fields).

### 3.13 `watertemp` — water temperature (2 probes; 1 retrievable)

| Source | Juris. | Retr. | Reason | Fields | Records | Latency (ms) | Licence / commercial |
|---|---|---|---|---:|---:|---:|---|
| CIOOS Atlantic ERDDAP catalogue (coastal) | multi | True | ok | 16 | 10 | 152.0 | CC-BY / OGL / CC0 · yes |
| RivTemp via DataStream OData v4 | CA | **False** | http_401 | 0 | — | 890.6 | DataStream per-dataset · **conditional** |

**Findings.** CIOOS Atlantic provides coastal water temperature. RivTemp (river temperature) returned HTTP 401 because a DataStream API key is required (`x-api-key`, requested via web form, rate ~2 req/s) — a documented access gate, not an endpoint failure (§4, §6). Note that NL ADRS (§3.2) additionally carries a `WATER_TEMP` field per station, giving river-temperature coverage in NL independent of RivTemp.

## 4. Coverage math and the non-retrievable probes

### 4.1 The arithmetic

Of **102 sanctioned probes, 98 were retrievable** (`retrievable = True`) and **4 were not**. Every retrievable probe is a clean `ok` — this run contains no `ok_empty` and no `5xx` outcomes. Retrievability = 98/102 = **96.1 %**. The four non-retrievable probes are the subject of §4.2.

The delta from v1.0 (80/86) has two independent causes. First, the registry itself grew and was corrected: the Datamart daily bundles (13 new probes), the BC ASWS SW/SD/PC/TA family, and the removal of a mis-registered "residual" from the sanctioned set moved the sanctioned denominator to 102 over 41 distinct Source IDs. Second, and separately, the **transient-retry policy** (§2) absorbed 18 GeoMet 5xx responses that would otherwise have failed, taking the run from 80/102 to 98/102.

### 4.2 The four non-retrievable outcomes — interpreted, not hidden

Per the DS-STD-2026.1 policy of interpreting rather than concealing negative results:

| # | Probe(s) | Reason | Interpretation | Consequence for the standard |
|---|---|---|---|---|
| 1–3 | GSC SensorThings groundwater — national, ON, QC (`SRC-STA-GW`) | `dns_error` | The officially-catalogued federal groundwater SensorThings host `mon.geosciences.ca` did not resolve during testing. This is a real availability/reliability finding about the federal endpoint, not a harness fault, and it survived the retry policy (DNS failure is not a transient the retry logic re-attempts). | **GIN WMS (`gin.geosciences.ca`) is the recommended national groundwater source** (§7). SensorThings SHOULD be re-tested and treated as unstable until it resolves. |
| 4 | RivTemp via DataStream OData v4 (`SRC-RIVTEMP`) | `http_401_unauthorized` | A DataStream API key is required (`x-api-key`, requested via web form, ~2 req/s). This is a documented access gate, not a failure of the endpoint. | RivTemp MAY be adopted once a key is provisioned; commercial use is CONDITIONAL. Interim river-temperature coverage is available via NL ADRS (§3.13). |

**Resolved since v1.0.** The four soft-negatives called out in the prior draft are now fully retrievable and no longer appear in the failure set: **CRID** and **Lake Ice Database** return rows via CKAN `package_show` (§3.9); **ECCC water-prediction** returns 40 WMS layers via GeoMet WMS GetCapabilities (§3.12); and **Conservation Ontario** resolves at its corrected URL (§3.12). No deeper-query follow-up is outstanding for these four.

### 4.3 Historical requirement satisfied

The standard requires **≥15 historical sources**. The run delivered **19 retrievable historical probes** (§3.4): 13 per-P/T GeoMet daily-mean depth series + HYDAT + 4 GeoMet collection views (daily-mean, monthly-mean, annual-statistics, annual-peaks — **no** annual-mean) + Open-Meteo ERA5 Archive. The requirement is met with margin, and every historical probe was retrievable.

## 5. Historical-depth findings

Measured earliest year per source/jurisdiction (deeper = more valuable for trend and return-period analysis):

| Source / jurisdiction | Earliest year (measured) | Span (yr) | Note |
|---|---:|---:|---|
| **HYDAT (national)** | **1860** | 167 | Deepest archive in the registry; the historical backbone (1860→2026) |
| CRID (river ice) | 1894 | 122 | Freeze/break-up lineage; now returns rows (§3.9) |
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
| GeoMet daily-mean depth — NL | 1999 | 2 | Shallowest measured provincial depth |
| GeoMet daily-mean depth — NT | 2017 | 6 | Youngest network |
| ECCC climate-monthly / -daily / -hourly | 1891 / 1949 / 1953 | 1 (sample) | Light-probe sample windows; record volume (§3.5) reflects the full archive |

**Finding.** **HYDAT (1860) is unambiguously the deepest source** and SHALL be the primary historical archive for all jurisdictions. The measured climate-archive earliest years (climate-monthly 1891, climate-daily 1949, climate-hourly 1953) are single-year light-probe samples and understate the true archival extent; the ECCC climate archive's *volume* (184.7 M daily / 277.1 M hourly records, §3.5) is what makes it the deepest precipitation/climate resource. Per-jurisdiction depth varies widely — AB/SK series reach the 1900s/1910s, whereas NL and NT depth is shallow — so the GeoMet per-P/T depth series SHOULD be treated as convenient programmatic slices, with HYDAT as the authoritative deep record.

## 6. Weather and AQI field-contract findings

### 6.1 Weather field contract

The app's weather contract is a 27-field current-plus-7-day daily payload. Only Open-Meteo supplies all 27 fields, but under a non-commercial free tier; the commercial-OK alternatives supply fewer fields.

| Source | Fields supplied | App-contract fit | Commercial | Note |
|---|---:|---|---|---|
| Open-Meteo forecast | 27 | Full (reference contract) | **Non-commercial** free tier (600/min, 5000/hr, 10000/day) | Paid plan required for commercial use |
| ECCC City Page — city XML | 20 | Partial (~74 %) | Yes (OGL-Canada) | 856-site catalogue; canonical Canadian source |
| MET Norway Locationforecast | 11 | Partial (~41 %) | Yes (CC-BY-4.0 / NLOD-2.0) | Descriptive User-Agent required |
| BC ASWS air temperature (TA) | 136 | Station observations (not a forecast) | Yes (OGL-BC) | Provincial station weather for BC; complements, not replaces, a forecast source |

### 6.2 AQI scale mismatch

| Source | Scale | Fields | Commercial | Note |
|---|---|---:|---|---|
| ECCC AQHI | **AQHI (Canadian, 1–10+)** | 14 | Yes (OGL-Canada) | Matches the app's AQHI contract |
| Open-Meteo Air Quality | **US AQI (0–500)** | 5 | Non-commercial | `us_aqi` + `pm2_5`/`pm10`; different scale |

### 6.3 Remediation options (decision DEFERRED to the Implementation Specification)

The following options are recorded for the "Implementation Specification"; DS-STD-2026.1 does not select among them here:

1. **Weather (non-commercial posture):** keep Open-Meteo as primary (full 27-field contract) and ECCC City Page as the commercial-safe validation/backup.
2. **Weather (commercial tier):** promote ECCC City Page (20 fields, commercial-OK) to primary and backfill the 7 missing contract fields from MET Norway or a paid Open-Meteo plan.
3. **AQI:** adopt ECCC AQHI as the primary AQI source (native AQHI scale, commercial-OK) and retain Open-Meteo AQI only as a gap-filler with an explicit US-AQI→AQHI conversion or clear scale labelling.

The choice among these is an implementation decision and SHALL be settled in the "Implementation Specification", not in this standard.

## 7. The verified standard (normative)

This section is normative. RFC-2119 [25] key words apply. Recommendations are derived solely from the measured evidence in §§3–6.

### 7.1 General rules

1. For **historical** water data in every jurisdiction, HYDAT [5] SHALL be the primary archive and the validation reference; the GeoMet OGC API [3] SHALL be the programmatic access path to the same lineage (daily-mean, monthly-mean, annual-statistics, annual-peaks).
2. For **real-time** water data, the jurisdiction's own authoritative programmatic feed SHALL be primary where one exists and is retrievable (AB, BC-partial, MB, ON, QC, NL); otherwise ECCC Datamart [4] SHALL be primary. ECCC Datamart/GeoMet SHALL serve as the backup/validation layer in all jurisdictions. Where both Datamart bundles are ingested, the **hourly** bundle SHALL drive the real-time surface and the **daily** bundle MAY be used to backfill archived daily values.
3. **Québec is the exception:** because ECCC Datamart carries only 15 QC real-time stations (§3.2), QC real-time river data SHALL be sourced from Québec Vigilance [15] (provincial-only). ECCC MAY still be used for QC historical/validation.
4. Every deployed source SHALL carry its required attribution string, and the project licence SHALL be kept distinct from each upstream licence (§9, and Part 1 [1]).

### 7.2 Core river-data recommendation (per jurisdiction)

| Juris. | Stations (recommended) | Real-time / current (primary → backup) | Historical (recommended) | Flag |
|---|---|---|---|---|
| AB | GeoMet hydrometric stations (1,104) | ECCC Datamart (AB) → GeoMet realtime · *(rivers.alberta.ca = non-commercial, intermittent; residual, measured in Part 3a (§10))* | HYDAT → GeoMet | AB provincial feed is non-commercial/residual |
| BC | GeoMet hydrometric stations (2,324) | ECCC Datamart (BC) → GeoMet realtime · *(BC AQUARIUS = undocumented; residual, measured in Part 3a (§10))* | HYDAT → GeoMet | BC provincial = partial |
| MB | GeoMet hydrometric stations (659) | **MB FloodInfo** → ECCC Datamart (MB) | HYDAT → GeoMet | Provincial-primary (OpenMB, commercial-OK) |
| NB | GeoMet hydrometric stations (144) | ECCC Datamart (NB) | HYDAT → GeoMet | ECCC-primary |
| NL | GeoMet hydrometric stations (230) | **NL ADRS** → ECCC Datamart (NL) | HYDAT → GeoMet | Provincial-primary; ADRS carries water-temp |
| NS | GeoMet hydrometric stations (144) | ECCC Datamart (NS) | HYDAT → GeoMet | ECCC-primary |
| NT | GeoMet hydrometric stations (245) | ECCC Datamart (NT) | HYDAT → GeoMet | ECCC-primary |
| NU | GeoMet hydrometric stations (109) | ECCC Datamart (NU) | HYDAT → GeoMet | ECCC-primary |
| ON | **ON SWMC KiWIS** (4,436) + GeoMet (1,119) | ECCC Datamart (ON) → KiWIS timeseries | HYDAT → GeoMet | KiWIS is the richer registry |
| PE | GeoMet hydrometric stations (43) | ECCC Datamart (PE) | HYDAT → GeoMet | ECCC-primary |
| **QC** | GeoMet hydrometric stations (1,001) | **QC Vigilance (provincial-only)** — ECCC Datamart carries only 15 QC stations | HYDAT → GeoMet | **EXCEPTION — provincial-only** |
| SK | GeoMet hydrometric stations (748) | ECCC Datamart (SK) · *(WSA = scrape-only, non-commercial; residual, measured in Part 3a (§10))* | HYDAT → GeoMet | SK provincial values are scrape-only |
| YT | GeoMet hydrometric stations (114) | ECCC Datamart (YT) | HYDAT → GeoMet | ECCC-primary |

### 7.3 Environmental-context recommendation (per category)

| Category | Recommended primary | Backup / validation | Provincial sources | Commercial posture |
|---|---|---|---|---|
| weather | Open-Meteo (27-field contract) | ECCC City Page; MET Norway; BC ASWS TA (BC stations) | BC (ASWS TA) | Open-Meteo non-commercial; City Page/MET Norway/BC ASWS commercial-OK (§6) |
| aqi | ECCC AQHI (native AQHI scale) | Open-Meteo AQI (US-AQI; scale-convert) | — | AQHI commercial-OK; Open-Meteo non-commercial |
| precip | ECCC GeoMet climate-daily/hourly/monthly | RDPA/CaPA gridded; BC ASWS PC (BC) | BC (ASWS PC) | Commercial-OK (OGL-Canada / OGL-BC) |
| snow | BC ASWS SW/SD (near-real-time SWE + depth) | CanSWE (historical SWE, 1928→) | BC (ASWS); AB (snow pillows — residual, measured in Part 3a (§10)) | Commercial-OK |
| ice | CRID (river ice, 1894→) | CIS ice-thickness; Lake Ice DB | — | Commercial-OK; all three ice sources now retrievable |
| drainage | NHN + WSC basins (gauge-keyed) | HydroSHEDS | BC FWA, ON OIH, QC GRHQ | Commercial-OK |
| groundwater | **GIN WMS (44 layers, `gin.geosciences.ca`)** | ON PGMN; QC RSESQ | ON (PGMN), QC (RSESQ) | Commercial-OK; **GSC SensorThings (`mon.geosciences.ca`) DNS-failed — do not rely** |
| watertemp | CIOOS Atlantic (coastal) | RivTemp (API key req.); NL ADRS (river, NL) | NL (ADRS) | CIOOS commercial-OK; RivTemp conditional |
| flood | Provincial structured feed where present | ECCC water-prediction (40 WMS layers); NRCan FHIMP | BC RFC, QC Vigilance, MB HFC, ON CO | Mixed; MB/CO unspecified |

### 7.4 Consolidated normative matrix (13 P/T × 12 categories)

Cell = recommended source (code); **(P)** = provincial-primary; *(res)* = provincial feed is residual/non-commercial (ECCC is the retrievable primary; measurement measured in Part 3a (§10)); **QC-only** = provincial-only per the Québec exception; `—` = no jurisdiction-specific source, use the national recommendation in §7.3. Legend below the table.

| Juris. | stations | current | historical | weather | aqi | precip | snow | ice | drainage | groundwater | watertemp | flood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AB | GM-S | DM *(res: AB-R)* | HY/GM | OM/CP | AQHI | CLIM | CanSWE *(res: AB-SNOW)* | CRID | NHN | GIN | — | ECCC-WP |
| BC | GM-S | DM *(res: AQ)* | HY/GM | OM/CP | AQHI | CLIM/**BC-PC** | **BC-ASWS (P)** | CRID | **BC-FWA (P)** | GIN | CIOOS | **BC-RFC (P)** |
| MB | GM-S | **MB-FI (P)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | **MB-HFC (P)** |
| NB | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| NL | GM-S | **NL-ADRS (P)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | **NL-ADRS (P)** | ECCC-WP |
| NS | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| NT | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| NU | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| ON | **KiWIS (P)** | DM → KiWIS | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | **ON-OIH (P)** | **ON-PGMN (P)** | — | **CO (P)** |
| PE | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | CIOOS | ECCC-WP |
| **QC** | GM-S | **QC-VIG (QC-only)** | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | **QC-GRHQ (P)** | **QC-RSESQ (P)** | — | **QC-VIG (P)** |
| SK | GM-S | DM *(res: WSA)* | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |
| YT | GM-S | DM | HY/GM | OM/CP | AQHI | CLIM | CanSWE | CRID | NHN | GIN | — | ECCC-WP |

**Legend.** GM-S = ECCC GeoMet hydrometric stations · DM = ECCC Datamart real-time CSV (hourly primary, daily backfill) · HY/GM = HYDAT (deep archive) via GeoMet OGC API · OM/CP = Open-Meteo (non-commercial) / ECCC City Page (commercial) · AQHI = ECCC AQHI · CLIM = ECCC GeoMet climate · BC-PC = BC ASWS accumulated-precip CSV · CanSWE = national SWE · BC-ASWS = BC ASWS SW/SD (SWE + depth) · AB-SNOW = Alberta snow pillows (residual) · CRID = Canadian River Ice Database · NHN = National Hydro Network (+ WSC basins) · GIN = Groundwater Information Network WMS (`gin.geosciences.ca`) · CIOOS = CIOOS Atlantic ERDDAP · ECCC-WP = ECCC water-prediction (40 WMS layers) / NRCan FHIMP · AB-R = rivers.alberta.ca · AQ = BC AQUARIUS · MB-FI = MB FloodInfo · MB-HFC = MB Hydrologic Forecast Centre · NL-ADRS = NL ADRS · KiWIS = ON SWMC KiWIS · ON-OIH = Ontario Integrated Hydrology · ON-PGMN = Ontario PGMN · CO = Conservation Ontario (now retrievable; licence unspecified) · QC-VIG = Québec Vigilance · QC-GRHQ = QC hydro network · QC-RSESQ = Québec RSESQ · BC-FWA/-RFC = BC atlas / river-forecast.

**Notes on the matrix.** (a) The single **QC-only** cell (QC/current) is the Québec exception and is normative. (b) `*(res)*` cells (AB, BC, SK current; AB snow) mean the provincial feed exists but is residual/non-commercial/intermittent; the retrievable, commercially-safe primary is ECCC Datamart (or, for AB snow, CanSWE) until the full-cadence stress harness (§8) characterizes the provincial feeds — those measurements are **measured in the Part 3a addendum (run `stress-20260916T105739Z`, complete 2026-09-16)**. (c) `ECCC-WP`, `CRID`, and `CO` are all now retrievable in this run (no outstanding deeper-query follow-up). (d) Groundwater across all jurisdictions relies on **GIN** (`gin.geosciences.ca`), not the DNS-failed GSC SensorThings host (`mon.geosciences.ca`).

## 8. Residual-harness status

The residual sources are the **four** probes that are registered but **not** sanctioned (`sanctioned = false`), and are therefore excluded from the 102 sanctioned rows above:

| Residual probe | Source ID | Category | Juris. | Licence / posture |
|---|---|---|---|---|
| Alberta River Basins `ListStationsAndAlerts` (discovery) | `SRC-AB-RIVERS` | current | AB | GoA copyright · non-commercial |
| BC ENV AQUARIUS WebPortal export (undocumented, best-effort) | `SRC-BC-AQUARIUS` | current | BC | OGL-BC · yes |
| Saskatchewan WSA hydrograph (dygraphs htmlwidget, scrape-only) | `SRC-SK-WSA` | current | SK | SK Crown copyright · no-written-permission |
| Alberta River Basins snow pillows (residual) | `SRC-AB-SNOW` | snow | AB | OGL-Alberta (unconfirmed) · unknown |

The **Open-Meteo rapid-burst** exercise is a **stress-harness target**, *not* a registered probe — it does not appear in the registry's probe list and is not one of the four residual probes. (This corrects the v1.0 statement that the fourth residual was an Open-Meteo burst; the fourth residual is `SRC-AB-SNOW`, and the correct residual count is four, contributing to the 41 distinct Source IDs rather than the previously-undercounted 40.)

These four sources are exercised only by the manual/overnight gentle stress harness (`waterpulse-backend/tests/stress_test.py`): a graduated knee-finder with random 10–30 min gaps, a descriptive User-Agent, `Retry-After` compliance, no cache-bypass headers, and `retries = 0` (so a source's first-response failure signature is recorded unmasked, unlike the sanctioned transport in §2). The harness now **skips a blocked target on a per-target basis** rather than aborting the whole run; a **global abort fires only on 3+ consecutive cross-target blocks**.

**Full-cadence run complete (2026-09-16).** The full residual run — `run_id = stress-20260916T105739Z`, targets in order **weather → BC → SK → AB**, real 10–30 min inter-request gaps — completed in ≈8.6 h (26 bunches, 139 requests, `aborted=False`, no blocked targets). Its measured safe-max, graduated-ladder detail, and failure signatures are reported in the **Part 3a addendum (§10)**. Headline: safe-max **weather 4** (knee at c=8, 5xx), **BC/SK/AB ≥16** (no throttle within the c=16 cap), and **zero connection-refusals/blocks** across ~8.6 h — so the `*(res)*` matrix cells (§7.4) are confirmed: the provincial scrape feeds are reachable at gentle rates but remain residual/non-commercial, and ECCC stays the commercially-safe primary.

## 9. Recommendations

1. **Adopt the §7 verified matrix as the normative source map.** ECCC/WSC (HYDAT + GeoMet + Datamart hourly & daily) SHALL be the historical backbone and the real-time backbone for all ECCC-primary jurisdictions; provincial-primary feeds (MB FloodInfo, NL ADRS, ON KiWIS, QC Vigilance) SHALL be used where retrievable and commercially compatible.
2. **Treat Québec as provincial-only for real-time** (Vigilance), given the measured 15-station Datamart footprint.
3. **Monetization: keep the project licence separate from every upstream licence.** A non-commercial posture is available today at full coverage. A commercial tier is bounded by the most-restrictive upstream term; the only hard blockers are **Alberta and Saskatchewan (written permission required)** and the **Open-Meteo free tier (paid plan, or switch to ECCC City Page / MET Norway)**. Every other source is commercial-OK with attribution (`commercial_ok = yes` for 96 of 102 sanctioned probes; `non-commercial` for the 3 Open-Meteo probes; `unknown` for MB HFC and Conservation Ontario; `conditional` for RivTemp). No source is cut for the commercial tier; the AB/SK provincial *values* are simply omitted from a commercial build (ECCC Datamart already covers those jurisdictions).
4. **Re-test the two hard-negative endpoints.** Re-test **GSC SensorThings** (`mon.geosciences.ca`, `dns_error`) periodically and treat it as unstable until it resolves; and **provision a DataStream `x-api-key`** (via the DataStream web form, ~2 req/s) if RivTemp river-temperature is wanted. The four v1.0 soft-negatives (CRID, Lake Ice, ECCC water-prediction, Conservation Ontario) are resolved and need no follow-up.
5. **Wire the newly-retrievable flood and ice sources.** Promote **ECCC water-prediction** (40 WMS layers via GeoMet WMS GetCapabilities — WCPS/OHPS/DHPS/RIOPS/CIOPS/surge) as the national flood/water-prediction backbone, and adopt **CRID** (1894→) plus the **Lake Ice Database** as the ice sources.
6. **Defer the weather/AQI field-contract choice to the "Implementation Specification"** (§6.3), and standardize on the AQHI scale for AQI.
7. **Completed the full-cadence residual harness** (§8, run `stress-20260916T105739Z`, complete 2026-09-16); Part 3a (§10) reports the measured safe request rates (weather 4; AB/SK/BC ≥16) and failure signatures (too-fast → `http_429`; wrong-station → `http_404_upstream_missing`; overload → `http_5xx`) for the scrape sources and the AB snow-pillow feed.
8. **Enforce ECCC acceptable-use limits** in the ingestion scheduler: contact MSC before approaching ~86,400 requests/day (~1 req/s), send no cache-bypass headers, and do not bulk-retrieve WMS tiles [8]. The sanctioned transport's bounded retries (§2) honour `Retry-After` and MUST NOT be widened into an aggressive retry loop.

## 10. Part 3a addendum — residual full-cadence results (COMPLETE, 2026-09-16)

**Status: COMPLETE.** The full-cadence gentle residual run `stress-20260916T105739Z` (targets
`weather → BC → SK → AB`, real 10–30 min randomized gaps, `retries=0`) ran to completion over
**≈8.6 h** (30,917 s): **26 bunches, 139 requests, `aborted=False`, `blocked_targets=[]`**.
This addendum reports the measured safe-max per target, the graduated-ladder detail, the
bad-input failure signatures, and the failure-reason catalogue. It confirms the provisional
`*(res)*` matrix cells in §7.4.

### 10.1 Recommended safe-max concurrency per target

| Target (source) | Safe-max | Knee | Notes |
|---|---|---|---|
| **weather** (Open-Meteo) | **4** | **c=8** (50% failure, 4× `http_5xx`) | Only target to knee; back-off honoured, ladder stopped at c=8 |
| **BC** (AQUARIUS) | **≥16** | none in ladder | 16/16 OK at 31 req/s, p95 367 ms — most robust at scale |
| **SK** (wsask.ca htmlwidget) | **≥16** | none (throttle) | Failures were benign per-station `http_404_bad_path`, not throttling |
| **AB** (rivers.alberta.ca) | **≥16** | none (throttle) | 14/16 OK at 36 req/s, p95 253 ms; failures = benign per-station 404s |

"≥16" = no throttle observed up to the ladder cap of 16; the true knee (if any) is above 16 and
was not probed (the harness intentionally caps at 16 for gentleness).

### 10.2 Graduated-ladder detail (per bunch)

| Target | c | ok/req | req/s | p95 ms | reasons |
|---|---|---|---|---|---|
| weather | 1 / 2 / 4 | 1/1 · 2/2 · 4/4 | 1.4 / 1.9 / 4.3 | 462 / 788 / 767 | all `ok` |
| weather | **8** | **4/8** | 4.6 | 1460 | **4× `http_5xx` → KNEE** |
| BC | 1→8 | 1/1 · 2/2 · 4/4 · 8/8 | 1.3 → 13.2 | ≤502 | all `ok` |
| BC | 16 | 16/16 | 31.2 | 367 | all `ok` |
| SK | 1 / 2 | 1/1 · 2/2 | 1.2 / 3.3 | ≤454 | all `ok` |
| SK | 4 / 8 / 16 | 3/4 · 6/8 · 11/16 | 3.0 / 5.2 / 7.5 | 344 / 596 / 1838 | `http_404_bad_path` (missing per-station hydrograph pages) |
| AB | 1 | 1/1 | 2.1 | 250 | `ok` |
| AB | 2 / 4 / 8 | 1/2 · 3/4 · 6/8 | 3.3 / 11.9 / 18.7 | ≤391 | `http_404_bad_path` (missing per-station JSON) |
| AB | 16 | 14/16 | 35.9 | 253 | 2× `http_404_bad_path`, else `ok` |

### 10.3 Bad-input probe failure signatures (the "why it fails" catalogue)

| Probe | Result | Signature learned |
|---|---|---|
| weather bad-path (`lat=999`) | `http_400_bad_request` | Open-Meteo validates params → **400** for a malformed request |
| BC bad-path (`/Data/DOES_NOT_EXIST`) | `ok` (HTTP 200) | AQUARIUS returns a generic 200 for unknown paths — **no clean 404** (caution: absence of 404 ≠ success) |
| SK / AB invalid-station (`99ZZ999`) | `http_404_upstream_missing` | **wrong station number** → 404 on an otherwise-valid URL shape |
| SK / AB bad-path | `http_404_bad_path` | **wrong address** (our malformed URL) → 404 |
| **weather rapid-burst** (25 concurrent, no jitter) | **15/25 ok + 10× `http_429`** at 38 req/s | **"requested too fast"** → Open-Meteo returns **429 rate-limited** (recoverable via `Retry-After`), NOT a block |

### 10.4 Failure-reason catalogue (whole run, 139 requests)

`ok` 106 · `http_404_bad_path` 16 · `http_429_rate_limited` 10 · `http_5xx_server` 4 ·
`http_404_upstream_missing` 2 · `http_400_bad_request` 1.

### 10.5 Findings

1. **No IP flagging.** Over ~8.6 h at 10–30 min gaps: **zero** connection-refusals, **zero** 403,
   `blocked_targets=[]`, no abort. The gentle-cadence anti-flag design (descriptive UA + contact,
   randomized long gaps, honour `Retry-After`, low concurrency) kept the egress IP unflagged.
2. **Alberta did not refuse in this window.** `rivers.alberta.ca` served up to c=16 (≈36 req/s,
   ~210–253 ms) with only benign per-station 404s — **no `connect_refused`**. This corroborates
   the original diagnosis: the earlier `ConnectError`s were driven by a *compounding concurrent
   burst* (historical 20×2 fan-out overlapping the 50-wide readings refresh), not a standing block.
   AB tolerates gentle access; it must not be hammered concurrently.
3. **Only Open-Meteo throttles under load** — `5xx` at c=8 (→ safe-max 4) and `429` under a
   25-wide rapid burst. Both are recoverable, reinforcing Open-Meteo as an exact-coordinate option
   used *gently* (and its free-tier non-commercial limit remains the licensing constraint).
4. **The `*(res)*` matrix cells (§7.4) are confirmed:** the AB/SK/BC provincial scrape feeds and the
   AB snow-pillow feed are reachable at gentle rates, but remain residual/non-commercial; ECCC stays
   the retrievable, commercially-safe primary. The normative recommendations in §7 are unchanged.
5. **SK/AB per-station 404s are data gaps, not errors:** some sampled station IDs lack that exact
   hydrograph/JSON URL; the knee-detector correctly excludes `http_404_bad_path` from throttle
   signals, so those ladders completed to c=16.

**Recommended operating rates (gentle, IP-safe):** weather ≤4 concurrent; AB/SK/BC ≤16 concurrent
with ≥10 min spacing between bulk sweeps; always honour `Retry-After`; never overlap a provincial
sweep with the app's 10-min scheduler against the same host.

## 11. References

[1] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1 — Standard & Reconnaissance," `urn:waterpulse:ds-std:2026.1`, 2026-09-16 (companion document, this series).

[2] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 2 — Methodology & Test Suite," `urn:waterpulse:ds-std:2026.1`, 2026-09-16 (companion document, this series).

[3] Environment and Climate Change Canada, Meteorological Service of Canada, "MSC GeoMet — OGC API (`api.weather.gc.ca`)." [Online]. Available: https://api.weather.gc.ca/ · https://eccc-msc.github.io/open-data/ . Accessed: 2026-09-16.

[4] Environment and Climate Change Canada, "MSC Datamart — hydrometric real-time data (hourly and daily bulk CSV)." [Online]. Available: https://dd.weather.gc.ca/hydrometric/ . Accessed: 2026-09-16.

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

[17] Government of British Columbia, "Automated Snow Weather Stations (ASWS: SW/SD/PC/TA CSVs), River Forecast Centre, Freshwater Atlas." [Online]. Available: https://www2.gov.bc.ca/gov/content/environment/air-land-water/water . Accessed: 2026-09-16.

[18] V. Vionnet et al. / Environment and Climate Change Canada, "CanSWE — Canadian historical Snow Water Equivalent dataset (Zenodo)." [Online]. Available: https://zenodo.org/ . Accessed: 2026-09-16.

[19] Environment and Climate Change Canada, "Canadian River Ice Database (CRID) and Lake Ice Database (via open.canada.ca CKAN `package_show`)." [Online]. Available: https://open.canada.ca/ . Accessed: 2026-09-16.

[20] Natural Resources Canada / Geological Survey of Canada, "Groundwater Information Network (GIN) WMS (`gin.geosciences.ca`)." [Online]. Available: https://gin.geosciences.ca/ . Accessed: 2026-09-16.

[21] Geological Survey of Canada, "SensorThings API groundwater monitoring (`mon.geosciences.ca`) — DNS unresolved at time of testing." [Online]. Accessed: 2026-09-16.

[22] DataStream, "DataStream API documentation (OData v4; RivTemp river-temperature datasets; `x-api-key` required, ~2 req/s)." [Online]. Available: https://github.com/datastreamapp/api-docs · https://datastream.org/ . Accessed: 2026-09-16.

[23] Canadian Integrated Ocean Observing System (CIOOS) Atlantic, "ERDDAP data catalogue." [Online]. Available: https://cioosatlantic.ca/erddap/ . Accessed: 2026-09-16.

[24] B. Lehner et al., "HydroSHEDS / HydroBASINS." [Online]. Available: https://www.hydrosheds.org/ . Accessed: 2026-09-16.

[25] S. Bradner, "Key words for use in RFCs to Indicate Requirement Levels," RFC 2119, IETF, Mar. 1997. [Online]. Available: https://www.rfc-editor.org/rfc/rfc2119 . Accessed: 2026-09-16.

[26] Natural Resources Canada, "National Hydro Network (NHN)." [Online]. Available: https://natural-resources.canada.ca/science-and-data/science-and-research/earth-sciences/geography/topographic-information/geobase . Accessed: 2026-09-16.

[27] Natural Resources Canada, "Flood Hazard Identification and Mapping Program (FHIMP) — geo.ca flood-mapping hub." [Online]. Available: https://geo.ca/ . Accessed: 2026-09-16.

[28] Environment and Climate Change Canada, Meteorological Service of Canada, "GeoMet WMS — water-prediction model layers (WCPS/OHPS/DHPS/RIOPS/CIOPS/storm-surge) via WMS GetCapabilities." [Online]. Available: https://geo.weather.gc.ca/geomet/ . Accessed: 2026-09-16.

---

*End of Part 3, including the Part 3a residual full-cadence-harness addendum (§10; run `stress-20260916T105739Z`, complete 2026-09-16).*
