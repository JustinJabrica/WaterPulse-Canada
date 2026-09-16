# WaterPulse Data-Source Standard — Implementation Specification

**Report ID:** DS-STD-2026.1
**Part:** Implementation Specification (companion to Parts 1–3)
**Version:** 1.0
**Status:** Draft
**Publication date:** 2026-09-16
**Prepared for:** WaterPulse-Canada
**Authoring organization:** WaterPulse Data Engineering
**Persistent identifier:** TBD (placeholder)

**How to cite:** WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part N," 2026-09-16.

---

## Abstract

This document is the engineering translation of the WaterPulse Data-Source Standard (DS-STD-2026.1). Where Parts 1–3 establish *which* sources are authoritative for each Canadian jurisdiction, *what* their measured coverage and usage rights are, and *how* the residual scrape sources behave under load, this Implementation Specification defines *how the WaterPulse backend (`waterpulse-backend/app`) shall be modified* to realize that standard. It specifies a per-jurisdiction source-priority resolver; a set of reusable transport adapters to be added under `app/services/providers`; the unification of two independent historical-retention constants into a single environment-driven control; a replacement of the two-digit drainage-basin heuristic with authoritative Water Survey of Canada (WSC) basin polygons; a decision framework for remediating the frontend's hard dependency on Open-Meteo weather and US AQI; the end-to-end propagation of Environment and Climate Change Canada (ECCC) quality-control symbols; optional new-category ingestion pipelines; and the guardrails required if the currently public-good, non-commercial service is ever monetized. No code is written in this round; the specification is scoped so that each section can be handed to a later build increment with acceptance criteria attached. All coverage claims are drawn from a single measured verification run (`run_id=probes-20260916T090344Z`, 2026-09-16), which retrieved 80 of 86 sanctioned probes in 186.7 s [1].

## Index Terms

Adapter pattern, air quality health index (AQHI), ArcGIS REST, data provenance, DataStream OData, drainage basin, Environment and Climate Change Canada (ECCC), ERDDAP, GeoMet OGC API, HYDAT, hydrometric data, KiWIS, MET Norway, Open-Meteo, open government licence, OGC API — Features, quality control, SensorThings, source-priority resolver, Water Survey of Canada (WSC).

---

## 1. Purpose and Scope

### 1.1 Purpose

This specification converts the normative positions of DS-STD-2026.1 Parts 1–3 [1][2][3] into a concrete, reviewable change plan for the WaterPulse backend. It is a design artifact: it names the files, models, functions, and configuration keys that SHALL change, states the data models that SHALL be introduced, and defines acceptance criteria for each change. It deliberately contains **no source code**; code is produced in a later build increment against the acceptance criteria stated here.

### 1.2 Scope

This document covers the server-side application rooted at `waterpulse-backend/app` and its verification harness at `waterpulse-backend/tests`. Frontend impacts (`waterpulse-frontend/src`) are described only where a backend contract changes what the frontend receives (Sections 6 and 7). Deployment, infrastructure, and the Caddy/Docker topology are out of scope except where a new environment variable is introduced (Sections 4 and 9).

### 1.3 Relationship to DS-STD-2026.1 Parts 1–3

| Source part | Establishes | Consumed by this spec in |
|---|---|---|
| Part 1 — Source registry & architecture | The 90-probe registry (86 sanctioned + 4 residual across 12 categories) and the primary/backup architecture: provincial-primary where a programmatic feed exists, ECCC/WSC as national backup and historical backbone; Quebec as a documented provincial-only exception [1] | §2, §3, §8 |
| Part 2 — Usage rights & monetization | Per-source licence and commercial posture; the non-commercial-vs-hypothetical-commercial two-tier model; the AB + SK + Open-Meteo-free-tier blockers [2] | §6, §9 |
| Part 3 — Residual harness addendum | Behaviour of the scrape/residual sources (AB `rivers.alberta.ca`, SK htmlwidget, BC AQUARIUS) and the Open-Meteo rapid-burst probe under the gentle overnight harness [3] | §9, §10 |

### 1.4 Current implementation baseline (as-built, 2026-09-16)

The following facts about the current codebase are load-bearing for the changes that follow and were verified by direct inspection:

- **Provider registry.** `app/services/providers/__init__.py` registers exactly two providers in a fixed priority order: `[AlbertaProvider(), ECCCProvider()]`. `get_active_providers()` returns this list; all three orchestrators loop over it and never reference a provider by name.
- **Current-reading merge.** `app/services/readings_refresh.py::_merge_readings()` implements priority purely by list order and first-writer-wins: "for each provider in registry order, keep the reading for a station only if no earlier provider already produced one." Provincial priority is therefore *implicit in registration order*, not driven by jurisdiction.
- **Historical fetch window.** `app/services/historical_sync.py` derives its fetch window from `settings.HISTORICAL_LOOKBACK_YEARS` (`config.py:87`, default `5`) at `historical_sync.py:108`.
- **Historical prune depth.** The prune step uses a *separate, hardcoded* module constant `MAX_YEARS = 5` at `historical_sync.py:37` (consumed in `_prune_old_data`, `historical_sync.py:311` and `:326`). The fetch window and the prune depth are **two independent values** that merely happen to both equal 5 today.
- **ECCC endpoints wired vs. used.** `config.py` defines convenience URLs for realtime, daily-mean, monthly-mean, annual-statistics, and annual-peaks. Only `eccc_realtime_url` (`eccc_provider.py:238`, `:292`) and `eccc_daily_mean_url` (`eccc_provider.py:383`) are actually called. Monthly-mean, annual-statistics, and annual-peaks are configured but **unused**.
- **Datamart base URL.** `ECCC_DATAMART_BASE_URL` is declared as a required `.env` value (`config.py:33`) but is referenced **nowhere** in `app/`. It is configured-but-dead.
- **Quality symbols.** `CurrentReading` already has `level_symbol` and `discharge_symbol` columns (`reading.py:30–31`), populated from `LEVEL_SYMBOL_EN`/`DISCHARGE_SYMBOL_EN` by the ECCC realtime parser (`eccc_provider.py:344–345`). No Datamart QA/QC grade is captured, and no symbol is surfaced through the API schema or frontend.
- **Drainage basin.** `Station.drainage_basin_prefix` (`station.py:26`, `String(5)`) stores the first two digits of the WSC station number. It powers `/api/readings/by-drainage-basin/{prefix}` (`routes/readings.py:171`), the station serializers (`routes/stations.py:198,363`), and the frontend "Drainage Basin" field (`StationDetail.js:506`).
- **Weather.** `app/services/weather.py` hard-codes an Open-Meteo request contract of 11 current variables, 13 daily variables, and 3 air-quality variables (US AQI + PM2.5 + PM10). `StationWeather.weather_data` stores the assembled `{current, daily_forecast, air_quality, elevation_m}` payload as JSON.

### 1.5 Gap statement

The current backend implements only 2 of the ~6 jurisdictions that have a programmatic provincial feed and none of the 12-category breadth catalogued in Part 1. Provincial priority is a side effect of list ordering rather than a declared policy, there is no Quebec-only rule, the historical archive is capped at ~5 years despite HYDAT offering a measured 1860→2026 record [1], drainage grouping is a two-digit heuristic rather than real geometry, and the weather/AQI layer depends on a source whose free tier is non-commercial [2]. This specification closes those gaps.

### 1.6 Requirements language

The key words "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", and "MAY" in this document are to be interpreted as described in RFC 2119 [24]. Normative requirements appear in the numbered "Requirements" lists within each section; all other prose is informative.

---

## 2. Per-Jurisdiction Source-Priority Resolver

### 2.1 Position

DS-STD-2026.1 Part 1 fixes the architecture: for each of the 13 provinces and territories, the **PRIMARY** source is that jurisdiction's own authoritative programmatic feed where one exists; the **BACKUP / validation** source is ECCC/WSC (Datamart real-time CSV, HYDAT deep history, GeoMet OGC metadata and historical, City Page, AQHI, climate). Only ~6 P/T have a real programmatic provincial river feed — Alberta, British Columbia (partial), Manitoba, Ontario, Quebec, and Newfoundland and Labrador; Saskatchewan values are scrape-only. The remainder are ECCC-primary. **Quebec is the documented exception**: because ECCC's Datamart carries only ~15 measured Quebec realtime stations [1], Quebec SHALL be treated as **provincial-only** (Vigilance), with ECCC used solely as historical/metadata backbone, never as the realtime backup for the current-reading merge.

The current implementation encodes priority implicitly through provider registration order (§1.4). This section replaces that with an **explicit, declarative resolver** that maps a `(jurisdiction, category, station)` tuple to an ordered list of sources.

### 2.2 Data model

A new module `app/services/resolver.py` SHALL define the source-priority policy as data, not control flow.

**`SourceRef`** — an immutable reference to one source in the Part 1 registry:

| Field | Type | Meaning |
|---|---|---|
| `source_id` | `str` | Registry ID, e.g. `SRC-ECCC-DATAMART`, `SRC-AB-RIVERS`, `SRC-QC-VIGILANCE` |
| `provider` | `str` | Adapter name that services this source (§3), e.g. `"eccc_datamart"`, `"alberta"`, `"qc_vigilance"` |
| `role` | `enum{PRIMARY, BACKUP, HISTORICAL, VALIDATION}` | Position in the priority chain |
| `commercial_ok` | `enum{yes, no, conditional, non_commercial}` | Copied from Part 2; consumed by §9 |
| `sanctioned` | `bool` | `False` for residual/scrape sources (AB rivers, SK htmlwidget, BC AQUARIUS) |

**`SourceRoute`** — the resolved ordered chain for one `(jurisdiction, category)` key:

| Field | Type | Meaning |
|---|---|---|
| `jurisdiction` | `str` | Two-letter P/T code, or `CA` for national |
| `category` | `str` | One of the 12 Part 1 categories (`current`, `historical`, `stations`, …) |
| `chain` | `list[SourceRef]` | Ordered `[provincial-primary, …, ECCC-backup]`; consumed head-first |
| `provincial_only` | `bool` | `True` only for QC `current` (and QC realtime-derived categories) |

The resolver SHALL be seeded from a static table (below) checked into the repository, so that priority is reviewable in one place and changes are captured in version control. The table is the machine-readable form of the Part 1 architecture; it SHALL NOT be inferred at runtime from provider registration order.

### 2.3 Resolver interface

```
resolve(jurisdiction: str, category: str, station: str | None = None) -> SourceRoute
```

- The resolver SHALL return the `SourceRoute` for the `(jurisdiction, category)` key.
- The optional `station` argument MAY be used for station-level overrides (e.g. a specific station whose provincial feed is known-dead falls straight through to ECCC). Station overrides SHOULD be stored in the same static table as an optional exceptions map and default to empty.
- The resolver SHALL be pure and side-effect-free; it performs no I/O. It answers "who, in what order" — the adapters (§3) and orchestrators (§2.5) perform the actual fetches.

### 2.4 The priority matrix (current + historical)

The following matrix is normative for the `current` (realtime) and `historical` categories and is derived directly from the Part 1 architecture and the measured run [1]. "ECCC realtime" denotes the Datamart bulk CSV / GeoMet hydrometric-realtime backup; "ECCC historical" denotes HYDAT + GeoMet daily/monthly/annual.

| Jurisdiction | Realtime PRIMARY | Realtime BACKUP | Provincial-only? | Historical backbone |
|---|---|---|---|---|
| AB | `SRC-AB-RIVERS` (residual/scrape; intermittent) | `SRC-ECCC-DATAMART` (AB) | no | HYDAT + GeoMet |
| BC | `SRC-BC-AQUARIUS` (residual; partial coverage) | `SRC-ECCC-DATAMART` (BC) | no | HYDAT + GeoMet |
| SK | — (values scrape-only, `SRC-SK-WSA`, residual) | `SRC-ECCC-DATAMART` (SK) | no | HYDAT + GeoMet |
| MB | `SRC-MB-FLOODINFO` (level/flow/forecast/alert) | `SRC-ECCC-DATAMART` (MB) | no | HYDAT + GeoMet |
| ON | `SRC-ON-KIWIS` (SWMC KiWIS) | `SRC-ECCC-DATAMART` (ON) | no | HYDAT + GeoMet |
| QC | `SRC-QC-VIGILANCE` (WFS) | **none** (ECCC carries only ~15 QC realtime stations) | **YES** | HYDAT + GeoMet |
| NL | `SRC-NL-ADRS` (per-station CSV) | `SRC-ECCC-DATAMART` (NL) | no | HYDAT + GeoMet |
| NB | — | `SRC-ECCC-DATAMART` (NB) | no | HYDAT + GeoMet |
| NS | — | `SRC-ECCC-DATAMART` (NS) | no | HYDAT + GeoMet |
| PE | — | `SRC-ECCC-DATAMART` (PE) | no | HYDAT + GeoMet |
| YT | — | `SRC-ECCC-DATAMART` (YT) | no | HYDAT + GeoMet |
| NT | — | `SRC-ECCC-DATAMART` (NT) | no | HYDAT + GeoMet |
| NU | — | `SRC-ECCC-DATAMART` (NU) | no | HYDAT + GeoMet |

Notes on the matrix, all measured [1]:

- ECCC Datamart per-jurisdiction record counts range from 5,571 rows / 9 stations (PE) to 317,748 rows / 523 stations (ON); QC returns only 9,191 rows / 15 stations — the evidence base for the QC exception.
- Residual primaries (AB, BC-AQUARIUS, SK) are `sanctioned=False` and MUST NOT be promoted to `PRIMARY` in a commercial tier without the licence remediation of §9. In the non-commercial tier they MAY be primary with attribution.
- For NB/NS/PE/YT/NT/NU there is no provincial programmatic river feed; these jurisdictions are ECCC-primary and the `chain` has a single entry.

### 2.5 Where the resolver plugs in

**2.5.1 Provider registry (`app/services/providers/__init__.py`).**
`get_active_providers()` returning a flat, order-encoded list SHALL be retained for backward compatibility but SHALL be superseded, for merge decisions, by the resolver. Providers SHALL be keyed by `name` in a registry dict (`{provider.name: instance}`) so the resolver's `SourceRef.provider` can be dereferenced to a live adapter. Registration order SHALL no longer carry semantic meaning.

**2.5.2 Current readings (`app/services/readings_refresh.py`).**
`_merge_readings()` (currently first-writer-wins by list order, `readings_refresh.py:141`) SHALL be reimplemented as a **resolver-driven merge**:

1. Group incoming `NormalizedReading` objects by `station_number`.
2. For each station, look up its `jurisdiction` (from `Station.province`) and call `resolve(jurisdiction, "current", station_number)`.
3. Walk the returned `chain` head-first; select the first source in the chain that produced a reading for that station. This makes provincial-primary win **by policy** rather than by registration order.
4. For QC stations where `provincial_only is True`, ECCC realtime readings SHALL be discarded for the `current` category even if present; only `SRC-QC-VIGILANCE` may satisfy realtime. ECCC MAY still supply QC *historical* rows.

The rating/percentile computation downstream of the merge is unchanged.

**2.5.3 Historical sync (`app/services/historical_sync.py`).**
`_sync_province()` currently filters stations to providers by `s.data_source == provider.name or "both"` (`historical_sync.py:140–144`). It SHALL instead consult `resolve(province, "historical", station)` to determine the ordered set of historical sources per station, with HYDAT + GeoMet as the backbone for **all** jurisdictions (including QC). Where a provincial source also offers validated history (e.g. NL ADRS carries `WATER_TEMP` and level/flow), the resolver MAY list it as a `VALIDATION` role behind the HYDAT/GeoMet `HISTORICAL` backbone; the merge into `historical_daily_means` SHALL keep the `HISTORICAL` value and record the validation source in `data_source`.

### 2.6 Requirements

- R2.1 The system SHALL express source priority as declarative data in `app/services/resolver.py`, seeded from the §2.4 matrix.
- R2.2 `_merge_readings()` SHALL select the current reading per station by walking the resolver chain head-first, not by provider registration order.
- R2.3 For QC `current`, the resolver SHALL set `provincial_only = True`; ECCC realtime readings for QC stations SHALL NOT be admitted to the current-reading merge.
- R2.4 The resolver SHALL be pure (no I/O) and unit-testable with a fixture table.
- R2.5 Residual/scrape sources (`sanctioned = False`) MAY be `PRIMARY` in the non-commercial tier but SHALL be demotable to non-primary via the §9 commercial guardrail without editing merge logic.

---

## 3. Reusable Transport Adapters

### 3.1 Position

Part 1 spans 12 categories and ~20 distinct upstream transports. The current `BaseProvider` ABC (`base_provider.py`) models a *jurisdiction provider* (`fetch_stations`, `fetch_latest_readings`, `fetch_historical_daily_means`). To cover the standard's breadth without one bespoke class per source, the system SHALL factor transport concerns into **reusable adapters** under `app/services/providers/adapters/`, and jurisdiction providers SHALL compose adapters rather than re-implement HTTP/parse logic.

An **adapter** encapsulates one wire protocol and one response shape; it produces the existing normalized dataclasses (`NormalizedStation`, `NormalizedReading`, `NormalizedDailyMean`) plus, for the new categories, the extension dataclasses of §8. Adapters SHALL NOT touch the database; they return normalized objects, preserving the current clean separation where orchestrators own all DB writes (`base_provider.py` docstring contract).

### 3.2 Adapter catalogue

The following adapters SHALL be added. "Measured" columns cite `run_id=probes-20260916T090344Z` [1].

| Adapter (module) | Wire protocol | Sources it services | Categories | Measured evidence [1] | Auth / notes |
|---|---|---|---|---|---|
| `eccc_datamart` | Bulk hourly CSV over HTTPS | `SRC-ECCC-DATAMART` (all 13 P/T) | current | 13 provinces retrievable; e.g. ON 317,748 rows/523 stn @7238 ms; QC 9,191/15 | **Wire the dead `ECCC_DATAMART_BASE_URL`** (`config.py:33`); 10 fields; OGL-Canada/ECCC v2.1.1 |
| `eccc_geomet_historical` | OGC API — Features (JSON) | `SRC-ECCC-GEOMET`, `SRC-ECCC-GEOMET-DAILY` | historical | monthly-mean, annual-statistics (1909→), annual-peaks (1923→) all `ok` | daily-mean **already wired** at `eccc_provider.py:383`; monthly/annual URLs exist in `config.py` but are **unused** — wire them here |
| `eccc_climate` | OGC API — Features (JSON) | `SRC-ECCC-CLIMATE` | precip, stations, weather | climate-daily 184.7 M rows (1876→), climate-hourly 277.1 M rows, climate-stations 8,435 | OGL-Canada; large volumes — paginate/stream |
| `eccc_citypage` | XML (city) + CSV (site catalogue) | `SRC-ECCC-CITYPAGE` | weather | Calgary city XML 20 fields; 856-site catalogue CSV | OGL-Canada/ECCC; candidate weather backstop (§6) |
| `eccc_aqhi` | OGC API — Features (JSON) | `SRC-ECCC-AQHI` | aqi | 6,996 obs / 10 stn @397 ms | AQHI 1–10 scale; feeds §6 AQHI→US-AQI mapping |
| `kiwis` | KiWIS REST (KISTERS) | `SRC-ON-KIWIS` | stations, current | `getStationList` 4,436 stations @2004 ms | Ontario SWMC; OGL-Ontario |
| `aquarius` | Aquarius Web Portal (undocumented) | `SRC-BC-AQUARIUS` | current | residual; smoke-validated in harness (Part 3) | OGL-BC; `sanctioned=False` — residual/scrape |
| `arcgis_rest` | ArcGIS REST FeatureServer (JSON) | `SRC-BC-RFC`, `SRC-MB-FLOODINFO`, `SRC-ON-OIH`, `SRC-NRCAN-FLOOD` | flood, current, drainage | MB FloodInfo 248 rows/30 fields @231 ms; BC-RFC 5 warnings | Per-jurisdiction OGL / OpenMB |
| `ogc_wfs` | OGC WFS (GeoJSON) | `SRC-QC-VIGILANCE`, `SRC-QC-GRHQ` | current, flood, drainage | QC Vigilance 50 stations/13 fields @505 ms | CC-BY-4.0 (Québec); Quebec provincial-only primary |
| `sensorthings` | OGC SensorThings API (JSON) | `SRC-STA-GW` (national/ON/QC) | groundwater | **DNS failure ×3** — host `mon.geosciences.ca` unresolvable | Fallback to `gin` (WMS) adapter — see §3.4 |
| `gin` | OGC WMS `GetCapabilities` | `SRC-GIN` | groundwater | 44 layers @797 ms | Working alternative to failing SensorThings host |
| `datastream_odata` | OData v4 (JSON) | `SRC-RIVTEMP` | watertemp | **HTTP 401** — API key required | Requires `x-api-key`; 2 req/s; commercial=conditional |
| `erddap` | ERDDAP tabledap (JSON/CSV) | `SRC-CIOOS` | watertemp | CIOOS Atlantic catalogue 10 rows/16 fields @164 ms | CC-BY / OGL / CC0 per dataset |
| `zenodo_dataset` | Static archive download + metadata | `SRC-CANSWE`, `SRC-CRID`, `SRC-LAKEICE` | snow, ice | CanSWE 4 rows (1928→) @4604 ms | Large downloads; run under `--no-downloads` in CI |
| `custom_ab` | Per-station static JSON | `SRC-AB-RIVERS` | current | residual; intermittent connection refusal (measured) | GoA copyright, non-commercial; existing `AlbertaProvider` refactors onto this |
| `custom_nl` | Per-station CSV | `SRC-NL-ADRS` | current, watertemp | 2,005 rows @599 ms; carries `WATER_TEMP` | OGL-NL |
| `custom_mb` | AGOL CSV + HTML/PDF | `SRC-MB-FLOODINFO`, `SRC-MB-HFC` | current, flood | FloodInfo 248 rows @231 ms; HFC HTML/PDF 0 fields | OpenMB; HFC is unstructured (parse best-effort) |
| `custom_qc` | CKAN + WFS | `SRC-QC-RSESQ`, `SRC-QC-GRHQ`, `SRC-QC-VIGILANCE` | groundwater, drainage, current | RSESQ 20 rows/53 fields @430 ms | CC-BY-4.0 (Québec) |

### 3.3 Adapter interface

A thin `SourceAdapter` protocol SHALL be introduced in `app/services/providers/adapters/base_adapter.py`:

- `name -> str` — matches `SourceRef.provider` in the resolver.
- `capabilities -> set[str]` — the categories this adapter can serve (e.g. `{"current", "historical"}`).
- Category-specific async fetch methods returning normalized objects, accepting an optional shared `httpx.AsyncClient` for connection pooling (mirroring the existing `client=` parameter convention at `eccc_provider.py:355`).
- Adapters SHALL classify their own failures using the harness's reason vocabulary (`dns_error`, `http_401_unauthorized`, `http_404_upstream_missing`, `ok_empty`, …) so operational monitoring is consistent with the probe evidence.

Existing `AlbertaProvider` and `ECCCProvider` SHALL be refactored to *compose* adapters: `ECCCProvider` composes `eccc_datamart` (realtime) + `eccc_geomet_historical` (history); `AlbertaProvider` composes `custom_ab`. This is a non-behavioural refactor for the two live providers and MUST be covered by the existing test suite before new adapters land.

### 3.4 Handling the six non-OK measured outcomes

The measured run returned six non-OK outcomes [1]; adapters SHALL interpret, not hide, them:

| Source | Outcome | Adapter behaviour |
|---|---|---|
| `SRC-STA-GW` ×3 | `dns_error` (host `mon.geosciences.ca` unresolvable) | `sensorthings` adapter SHALL surface a health warning and the resolver SHALL fall through to the `gin` WMS adapter for groundwater |
| `SRC-RIVTEMP` | `http_401_unauthorized` | `datastream_odata` SHALL treat missing `x-api-key` as a *configuration* state, not an endpoint failure; disabled until a key is provided |
| `SRC-ON-CO` | `http_404_upstream_missing` (page moved, HTML-only) | No adapter; documented as unavailable pending a machine-readable endpoint |
| `SRC-ECCC-WATERPRED`, `SRC-CRID`, `SRC-LAKEICE` | `ok_empty` (reachable; light sample returned no rows/file link) | Adapters SHALL mark the source reachable and schedule a deeper query rather than reporting failure |

### 3.5 Requirements

- R3.1 New adapters SHALL live under `app/services/providers/adapters/` and SHALL NOT perform database writes.
- R3.2 The `eccc_datamart` adapter SHALL consume `ECCC_DATAMART_BASE_URL` (`config.py:33`), eliminating the configured-but-dead value.
- R3.3 The `eccc_geomet_historical` adapter SHALL wire the currently-unused `eccc_monthly_mean_url`, `eccc_annual_stats_url`, and `eccc_annual_peaks_url`; it SHALL NOT duplicate the daily-mean path already implemented at `eccc_provider.py:383`.
- R3.4 Each adapter SHALL declare `capabilities` consumed by the resolver, and SHALL reuse a passed `httpx.AsyncClient` when provided.
- R3.5 `AlbertaProvider` and `ECCCProvider` SHALL be refactored to compose adapters with no change to their externally observed behaviour, verified against the existing test suite.
- R3.6 The `datastream_odata` adapter SHALL require `x-api-key` from configuration and SHALL honour the documented 2 req/s ceiling.

---

## 4. Environment-Driven Historical Depth

### 4.1 Position

Two independent constants currently govern historical retention, and they are conflated only by coincidence of value:

1. **Fetch window** — `settings.HISTORICAL_LOOKBACK_YEARS` (`config.py:87`, default `5`) sets how far back `_sync_province()` requests daily means (`historical_sync.py:106–109`): `start_date = now - 365 * HISTORICAL_LOOKBACK_YEARS`.
2. **Prune depth** — a hardcoded module constant `MAX_YEARS = 5` (`historical_sync.py:37`) sets how many years `_prune_old_data()` keeps per `(station, data_key, month_day)` group (`historical_sync.py:311`, `:326`).

Changing the environment variable today silently does **not** change the prune depth, so a deployment could fetch 20 years and then immediately prune 15 of them away. DS-STD-2026.1 requires that the deep validated archive be available; HYDAT is that archive, with a **measured span of 1860→2026 (167 years, 6,478 stations, 1,779,871 records)** [1].

### 4.2 Change

A single environment-driven control SHALL govern both fetch and prune.

- A configuration key `HISTORICAL_DEPTH_YEARS` SHALL be introduced on `Settings` (replacing/absorbing `HISTORICAL_LOOKBACK_YEARS`; the old name MAY be retained as a deprecated alias for one release).
- **Both** the fetch window (`historical_sync.py:106–109`) and the prune depth (`MAX_YEARS`, `historical_sync.py:37`) SHALL read this single value. The hardcoded `MAX_YEARS = 5` SHALL be removed.
- **`0` or unset SHALL mean "full record"**: the fetch window SHALL be unbounded (request the entire available history from the source), and the prune step SHALL be a no-op (retain all years). A sentinel of `0` is preferred over a magic large number.
- When `HISTORICAL_DEPTH_YEARS = N > 0`, the fetch window SHALL be `now - N years` and the prune SHALL retain the most recent `N` years per `(station, data_key, month_day)` group, exactly as `_prune_old_data` does today but with `N` substituted for `MAX_YEARS`.

### 4.3 Interaction with sources

- HYDAT (via the `zenodo_dataset`/HYDAT path) is the intended backing for a full-record (`0`) configuration and is the only source with the measured 1860→2026 depth [1]. GeoMet daily-mean per-jurisdiction spans are shallower and vary (e.g. AB earliest 1908, NL earliest 1999) [1]; the resolver's `HISTORICAL` backbone (§2.5.3) SHALL prefer HYDAT for deep history and GeoMet for recent daily means.
- Operators SHOULD be warned in documentation that `HISTORICAL_DEPTH_YEARS = 0` against HYDAT implies large volumes (order 1.78 M records nationally) and correspondingly longer sync/prune times.

### 4.4 Requirements

- R4.1 A single `HISTORICAL_DEPTH_YEARS` config key SHALL drive both the fetch window and the prune depth.
- R4.2 `MAX_YEARS = 5` at `historical_sync.py:37` SHALL be removed; `_prune_old_data` SHALL read the config value.
- R4.3 A value of `0` or unset SHALL mean full record: unbounded fetch window and no-op prune.
- R4.4 The full-record configuration SHALL source deep history from HYDAT (measured 1860→2026), not GeoMet.

---

## 5. Real Drainage Basins

### 5.1 Position

`Station.drainage_basin_prefix` (`station.py:26`) stores the first two digits of the WSC station number as a proxy for drainage basin. This two-digit heuristic drives national grouping via `/api/readings/by-drainage-basin/{prefix}` (`routes/readings.py:171`), the station serializers (`routes/stations.py:198,363`), and the frontend "Drainage Basin" field (`StationDetail.js:506`). It is an approximation of WSC's *major drainage area* code, not a real watershed boundary.

DS-STD-2026.1 lists `SRC-WSC-BASINS` — WSC gauge drainage-basin polygons keyed to the WSC `STATION_NUMBER` (OGL-Canada-2.0, commercial=YES, measured retrievable [1]) — as the authoritative source. This section replaces the heuristic with real, per-gauge basin geometry.

### 5.2 Change

- A new table `station_basins` SHALL be introduced, keyed by `station_number` (FK to `stations.station_number`), storing at minimum: `wsc_station_number`, `drainage_area_km2`, and an **optional geometry** column for the basin polygon.
- Geometry storage SHALL be optional and pluggable: where PostGIS is available, a `GEOMETRY(MultiPolygon, 4326)` column SHOULD be used; otherwise the polygon MAY be stored as GeoJSON in a JSON column, or omitted entirely (attributes-only) for deployments that only need the basin attributes and the join.
- Basin data SHALL be ingested via a `drainage_gis` pipeline (see §8) from `SRC-WSC-BASINS`, joined to stations on `STATION_NUMBER`.
- `drainage_basin_prefix` SHALL be **retained but demoted** to a coarse fallback grouping. The `/by-drainage-basin` grouping SHOULD migrate to the real basin identifier (WSC major drainage area / sub-sub-drainage) sourced from the new table; the endpoint contract MAY keep the `{prefix}` path parameter for one release, resolving it against the richer data.

### 5.3 Requirements

- R5.1 A `station_basins` table keyed to WSC `STATION_NUMBER` SHALL be added, with an optional geometry column (PostGIS geometry or GeoJSON JSON).
- R5.2 Basin polygons SHALL be sourced from `SRC-WSC-BASINS` and joined to stations on `station_number`.
- R5.3 `drainage_basin_prefix` MAY be retained as a coarse fallback but SHALL NOT be the authoritative basin identifier once `station_basins` is populated.
- R5.4 The migration SHALL preserve the existing `/api/readings/by-drainage-basin/{prefix}` contract for at least one release.

---

## 6. Weather / AQI Remediation Decision

### 6.1 Position

The frontend hard-depends on a rich forecast contract currently supplied only by Open-Meteo (`weather.py`): current `apparent_temperature`, `relative_humidity_2m`, `visibility`, `uv_index`, `wind_gusts_10m`, `is_day`; daily `precipitation_probability_max` and a **7-day** daily block; and air quality as **US AQI (0–500)** plus PM2.5 and PM10. Per Part 2, Open-Meteo's free tier is CC-BY-4.0 but **non-commercial only** (600/min, 5,000/hr, 10,000/day); commercial use requires a paid plan [2]. ECCC City Page (20 fields, measured [1]) and AQHI (1–10 scale, measured [1]) cannot fully reproduce this contract.

### 6.2 Field-coverage decision matrix

Coverage of the frontend's hard-required fields by candidate source (measured field availability [1]; "✓" = directly available, "~" = derivable/approximate, "✗" = not available):

| Required field | Open-Meteo (current) | MET Norway Locationforecast | ECCC City Page | ECCC AQHI |
|---|---|---|---|---|
| `apparent_temperature` | ✓ | ✓ | ✗ | — |
| `relative_humidity` | ✓ | ✓ | ✓ | — |
| `visibility` | ✓ | ✗ | ~ (text conditions) | — |
| `uv_index` | ✓ | ✓ (UV forecast) | ✗ | — |
| `wind_gusts` | ✓ | ✓ | ~ | — |
| `precipitation_probability` | ✓ | ✓ | ✗ | — |
| `is_day` | ✓ | ~ (derive from sunrise/sunset) | ~ | — |
| 7-day daily forecast | ✓ | ✓ (up to ~9 days) | ~ (short-range) | — |
| US AQI (0–500) | ✓ | ✗ | ✗ | ✗ (AQHI 1–10 only) |
| PM2.5 / PM10 | ✓ | ✗ | ✗ | ~ (AQHI includes PM2.5 as input) |
| Exact-coordinate query | ✓ | ✓ | ✗ (nearest of 856 city sites) | ✗ (nearest of 10 AQHI stns) |
| Commercial use | ✗ (paid plan) | ✓ (CC-BY-4.0 / NLOD-2.0) | ✓ (OGL-Canada) | ✓ (OGL-Canada) |

### 6.3 Recommendation

Two viable paths; the project SHALL choose one explicitly:

- **Option A — Keep Open-Meteo (status quo, non-commercial).** Zero engineering change. Acceptable *only* while the service remains non-commercial. Blocks monetization (§9) until switched.
- **Option B — Switch the rich forecast to MET Norway Locationforecast (RECOMMENDED for a monetization-ready posture).** MET Norway is exact-coordinate, commercial-OK (CC-BY-4.0 / NLOD-2.0), and covers apparent temperature, humidity, UV, wind gusts, precipitation probability, and a multi-day daily block [1][2]. Gaps and mitigations:
  - **`visibility`** — not provided by MET Norway. Either drop the field from the required contract or backfill from ECCC City Page's textual conditions (`~`). RECOMMENDED: make `visibility` optional in the contract.
  - **`is_day`** — derive from MET Norway sunrise/sunset (the existing code already extracts sunrise/sunset from the daily block, `weather.py:114–117`).
  - **Air quality** — MET Norway does not provide US AQI/PM. RECOMMENDED: source AQI from **ECCC AQHI** (commercial-OK) and either (a) map **AQHI (1–10) → US-AQI bands** for display continuity, or (b) switch the frontend AQI presentation to AQHI natively and keep PM2.5/PM10 from AQHI's constituent inputs where exposed. The AQHI→US-AQI mapping SHALL be documented as an approximation (the two indices are not linearly equivalent).

A hybrid is explicitly permitted: MET Norway for forecast + ECCC AQHI for air quality gives a fully commercial-OK weather/AQI stack with no Open-Meteo dependency.

### 6.4 Abstraction

Regardless of choice, `weather.py`'s hard-coded Open-Meteo variable lists (`CURRENT_VARIABLES`, `DAILY_VARIABLES`, `AIR_QUALITY_VARIABLES`) SHALL be moved behind a weather adapter interface (§3) so the source is swappable without touching the `StationWeather.weather_data` JSON contract consumed by the frontend. The assembled payload shape `{current, daily_forecast, air_quality, elevation_m}` SHALL be preserved.

### 6.5 Requirements

- R6.1 The project SHALL record an explicit decision between Option A (keep Open-Meteo, non-commercial) and Option B (MET Norway + ECCC AQHI, commercial-ready).
- R6.2 The weather source SHALL be placed behind an adapter so it is swappable without changing the `StationWeather.weather_data` contract.
- R6.3 If Option B is chosen, `visibility` SHALL be made optional and `is_day` SHALL be derived from sunrise/sunset.
- R6.4 Any AQHI→US-AQI mapping SHALL be documented as an approximation.
- R6.5 A commercial tier (§9) SHALL NOT ship on the Open-Meteo free tier.

---

## 7. QA/QC Symbol Propagation

### 7.1 Position

ECCC carries qualitative quality symbols on realtime and daily records — `LEVEL_SYMBOL_EN` and `DISCHARGE_SYMBOL_EN` (e.g. estimated, ice-affected, provisional) — and the Datamart CSV carries a QA/QC grade. The database already has `level_symbol` and `discharge_symbol` columns on `CurrentReading` (`reading.py:30–31`), populated by the ECCC realtime parser (`eccc_provider.py:344–345`) and carried through the upsert (`readings_refresh.py:310–317, 341–342`). However, these symbols are **not exposed through the API schema and not surfaced in the UI**, and no Datamart QA/QC grade is captured.

### 7.2 Change

- The ECCC/Datamart QA/QC grade SHALL be captured. A `qa_qc_grade` field SHOULD be added to `NormalizedReading` (`base_provider.py`) and to `CurrentReading`, populated by the `eccc_datamart` adapter (§3). The existing `extra` JSON MAY hold provider-specific grade codes, but the primary grade SHOULD be a first-class column for query/filtering.
- `level_symbol`, `discharge_symbol`, and `qa_qc_grade` SHALL be added to the reading response schema in `app/schemas/__init__.py` and returned by the readings routes so the frontend can display provenance/quality badges.
- The frontend SHOULD render these as a quality/provenance indicator on the station reading (e.g. an "ice-affected" or "estimated" badge), analogous to the existing rating chips.
- Symbols SHALL NOT alter the numeric value or the percentile rating; they annotate it.

### 7.3 Requirements

- R7.1 `level_symbol` and `discharge_symbol` SHALL be exposed through the reading API schema and returned by the readings routes.
- R7.2 A `qa_qc_grade` field SHALL be added to `NormalizedReading` and `CurrentReading` and populated by the `eccc_datamart` adapter.
- R7.3 Quality symbols SHALL be presented in the UI as annotations and SHALL NOT modify numeric values or ratings.

---

## 8. New-Category Ingestion Pipelines (Optional)

### 8.1 Position

Part 1 catalogues nine categories beyond `current`/`historical`/`stations`. Each MAY be added as an independent, optional pipeline that reuses the §3 adapters and writes to a category-specific model. These pipelines are opt-in and SHALL be feature-flagged so the core hydrometric product is unaffected when they are disabled.

### 8.2 Pipelines

| Category | Sources (measured [1]) | Adapter(s) | New model (proposed) | Notes |
|---|---|---|---|---|
| Snow (SWE) | `SRC-CANSWE` (national, 1928→), `SRC-BC-ASWS` (121 stn, 8,409 rows) | `zenodo_dataset`, `arcgis_rest`/CSV | `snow_swe` | CanSWE is a large download — gate behind `--no-downloads` in CI |
| Ice | `SRC-CRID` (196 NHP sites, 1894→), `SRC-CIS-ICE`, `SRC-LAKEICE` | `zenodo_dataset` | `river_ice` | CRID/LakeIce returned `ok_empty` — needs a deeper query (§3.4) |
| Groundwater | `SRC-GIN` (44 WMS layers), `SRC-ON-PGMN`, `SRC-QC-RSESQ` | `gin` (WMS), `custom_qc`/CKAN | `groundwater_obs` | National SensorThings host is down (`dns_error`); GIN WMS is the working path |
| Precip | `SRC-ECCC-CLIMATE` (climate-daily/hourly/monthly, RDPA/CaPA) | `eccc_climate` | `precip_obs` | Very large volumes (100M+ rows); ingest selectively by station/date |
| Drainage GIS | `SRC-WSC-BASINS`, `SRC-NHN`, `SRC-BC-FWA`, `SRC-ON-OIH`, `SRC-QC-GRHQ`, `SRC-HYDROSHEDS` | `arcgis_rest`, `ogc_wfs` | `station_basins` (§5) | Powers §5 real drainage basins |
| Water temp | `SRC-CIOOS` (Atlantic ERDDAP), `SRC-RIVTEMP` (needs key), `SRC-NL-ADRS` (`WATER_TEMP`) | `erddap`, `datastream_odata`, `custom_nl` | `water_temp_obs` | RivTemp needs `x-api-key` |
| Flood | `SRC-BC-RFC`, `SRC-MB-HFC`, `SRC-QC-VIGILANCE`, `SRC-NRCAN-FLOOD` | `arcgis_rest`, `ogc_wfs` | `flood_warning` | Conservation Ontario (`SRC-ON-CO`) is 404/HTML-only — excluded until an API exists |
| AQI | `SRC-ECCC-AQHI`, `SRC-OPEN-METEO-AQI` | `eccc_aqhi` | (reuse `StationWeather.air_quality`) | Feeds §6 |
| Weather | `SRC-ECCC-CITYPAGE`, `SRC-MET-NORWAY`, `SRC-OPEN-METEO` | `eccc_citypage`, MET adapter | (reuse `StationWeather`) | Feeds §6 |

### 8.3 Requirements

- R8.1 Each new-category pipeline SHALL be independently feature-flagged and default-off.
- R8.2 New-category pipelines SHALL reuse §3 adapters and SHALL NOT bypass the adapter/orchestrator separation.
- R8.3 Large-volume sources (CanSWE, ECCC climate, HYDAT) SHALL support a bounded/selective ingest mode for CI and low-resource deployments.

---

## 9. Commercial-Tier Guardrails

### 9.1 Position

The service is currently public-good and non-commercial. Part 2 establishes that a hypothetical commercial tier is capped by the **most-restrictive upstream term**, and identifies the specific blockers [2]:

- **Alberta `rivers.alberta.ca`** — Government of Alberta copyright; commercial = **NO** without written permission; `sanctioned=False`; intermittent connection refusal (measured [1][3]).
- **Saskatchewan WSA** — SK Crown copyright; commercial = **NO** without written permission; values scrape-only.
- **Open-Meteo free tier** — commercial requires a paid plan; otherwise non-commercial only [2].
- Everything else is commercial-OK **with attribution** (ECCC OGL-Canada/ECCC v2.1.1; provincial OGL-\<jurisdiction\>; MB OpenMB; QC CC-BY-4.0; MET Norway CC-BY-4.0/NLOD-2.0; HydroSHEDS; CIOOS). RivTemp is **conditional** (per-dataset licence + API key).

### 9.2 Change — a commercial gate

A configuration flag `COMMERCIAL_MODE` (default `False`) SHALL gate source admissibility, enforced **in the resolver (§2)**, not scattered through adapters:

- When `COMMERCIAL_MODE = True`, the resolver SHALL exclude any `SourceRef` whose `commercial_ok` is `no` or `non_commercial`. Concretely, this drops `SRC-AB-RIVERS`, `SRC-SK-WSA`, and the Open-Meteo free tier from all chains.
- Dropped provincial realtime SHALL fall through to the ECCC backup already in the chain (Datamart AB/SK), so coverage degrades gracefully rather than disappearing. AB/SK become ECCC-primary in commercial mode.
- The weather/AQI stack SHALL switch off Open-Meteo to **MET Norway + ECCC AQHI/City Page** (§6, Option B). `COMMERCIAL_MODE = True` SHALL be incompatible with an Open-Meteo weather adapter and the system SHALL refuse to start in that combination (fail-fast configuration validation).
- RivTemp (`conditional`) MAY be admitted in commercial mode only when a valid `x-api-key` and per-dataset commercial licence are configured.

### 9.3 Attribution enforcement

Each `SourceRef` carries its required attribution string (from Part 2). The API SHALL emit, per response and/or in an app-wide credits surface, the attribution for every source that contributed data, including but not limited to:

- ECCC: "Data Source: Environment and Climate Change Canada".
- Manitoba: "Contains information … OpenMB Information and Data Use License (Manitoba.ca/OpenMB)".
- Provincial OGL: "Contains information licensed under the Open Government Licence – \<jurisdiction\>".
- Quebec: attribute "Gouvernement du Québec".
- MET Norway: "Data from MET Norway" with a descriptive User-Agent on every request.
- Open-Meteo (non-commercial tier only): "Weather data by Open-Meteo.com".

The **project licence** SHALL be kept distinct from each **upstream licence**; the credits surface SHALL make this separation explicit.

### 9.4 Acceptable-use ceilings

Adapters SHALL respect the measured/known upstream ceilings: ECCC contact-MSC threshold ≈ 86,400 req/day (~1 req/s), no cache-bypass headers, no bulk WMS-tile retrieval; Open-Meteo 600/min·5,000/hr·10,000/day (non-commercial); DataStream 2 req/s; MET Norway descriptive UA required. These SHALL be enforced by the existing retry/back-off machinery (`WEATHER_MAX_RETRIES`, `WEATHER_BATCH_DELAY`) generalized to all adapters.

### 9.5 Requirements

- R9.1 A `COMMERCIAL_MODE` flag SHALL gate source admissibility in the resolver.
- R9.2 In commercial mode the resolver SHALL exclude `commercial_ok ∈ {no, non_commercial}` sources (AB portal, SK WSA, Open-Meteo free tier) and fall through to ECCC backups.
- R9.3 Commercial mode SHALL fail-fast if configured with an Open-Meteo weather adapter.
- R9.4 The system SHALL emit the correct attribution string for every contributing source and keep the project licence distinct from upstream licences.
- R9.5 All adapters SHALL enforce the documented upstream acceptable-use ceilings.

---

## 10. Migration, Rollout, and Testing

### 10.1 Rollout phases

The changes are sequenced so each phase is independently shippable and reversible:

| Phase | Delivers | Depends on | Risk |
|---|---|---|---|
| P0 | Adapter base + refactor `AlbertaProvider`/`ECCCProvider` onto adapters (§3.3, non-behavioural) | — | Low; guarded by existing tests |
| P1 | Resolver module + resolver-driven `_merge_readings` + QC provincial-only (§2) | P0 | Medium; changes merge semantics |
| P2 | Wire `eccc_datamart` (dead URL) + `eccc_geomet_historical` (unused monthly/annual URLs) (§3) | P0 | Low |
| P3 | Unify historical depth into one env var; full-record via HYDAT (§4) | — | Low; config-only + prune change |
| P4 | QA/QC symbol exposure (§7) | P2 (Datamart grade) | Low |
| P5 | Weather/AQI decision + weather adapter (§6) | P0 | Medium; frontend contract-sensitive |
| P6 | Real drainage basins `station_basins` (§5) + `drainage_gis` pipeline (§8) | P0 | Medium; new table/migration |
| P7 | Optional new-category pipelines (§8), feature-flagged | P0–P2 | Low; default-off |
| P8 | Commercial-tier guardrails (§9) | P1, P5 | Low; gated by flag |

### 10.2 Database migrations

New Alembic migrations SHALL be authored (following the existing `alembic/versions/` pattern) for: `qa_qc_grade` on `current_readings` (§7); the `station_basins` table (§5); and any new-category tables activated in P7 (§8). Migrations SHALL be additive and reversible; no destructive change to `drainage_basin_prefix` is permitted while it remains a fallback (§5.2).

### 10.3 Configuration changes

`.env`/`Settings` additions: `HISTORICAL_DEPTH_YEARS` (replaces `HISTORICAL_LOOKBACK_YEARS`, §4); `COMMERCIAL_MODE` (§9); `DATASTREAM_API_KEY` for RivTemp (§3, §8); and a `WEATHER_SOURCE` selector (§6). `ECCC_DATAMART_BASE_URL`, currently required-but-dead, becomes live (§3, R3.2).

### 10.4 Testing and verification

- **Regression gate.** The existing backend test suite SHALL pass unchanged after the P0 adapter refactor, proving the refactor is non-behavioural.
- **Source verification.** After P2 and each subsequent phase that touches a source, the sanctioned probe harness SHALL be re-run to confirm coverage is maintained:

  ```
  docker-compose run --rm -w /app backend python -m tests.probe_sources
  docker-compose run --rm -w /app backend python -m tests.probe_sources --category current
  docker-compose run --rm -w /app backend python -m tests.probe_sources --source SRC-ECCC-DATAMART
  ```

  The pass bar is the measured baseline: **80/86 sanctioned probes retrievable** [1]. The six known non-OK outcomes (§3.4) are expected and SHALL be interpreted, not counted as regressions, unless a previously-OK source degrades.
- **Resolver unit tests.** The resolver (§2) SHALL have table-driven unit tests asserting: provincial-primary precedence per jurisdiction; QC provincial-only (no ECCC realtime admitted); and `COMMERCIAL_MODE` exclusion of AB/SK/Open-Meteo (§9).
- **Historical depth tests.** Tests SHALL assert that `HISTORICAL_DEPTH_YEARS = 0` yields an unbounded fetch and a no-op prune, and that `N > 0` fetches `N` years and prunes to `N` (§4).
- **Residual harness.** The residual/scrape sources SHALL continue to be exercised only by the user-launched gentle overnight harness (`tests/stress_test.py`); its dated results become the Part 3 addendum [3] and SHALL NOT run in CI.

### 10.5 Acceptance criteria (summary)

The implementation is complete when: (a) source priority is declarative and resolver-driven with QC provincial-only enforced (§2); (b) the dead Datamart URL and unused GeoMet historical URLs are live (§3); (c) a single env var governs historical fetch+prune with a working full-record mode backed by HYDAT (§4); (d) `station_basins` carries real WSC basin geometry keyed to `STATION_NUMBER` (§5); (e) the weather/AQI source is behind a swappable adapter with a recorded source decision (§6); (f) QA/QC symbols reach the API and UI (§7); (g) `COMMERCIAL_MODE` correctly gates AB/SK/Open-Meteo and enforces attribution (§9); and (h) `tests.probe_sources` still reports ≥ 80/86 sanctioned probes retrievable with no previously-OK source regressed (§10.4).

---

## References

[1] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1 — Source Registry and Architecture," 2026-09-16. Measured verification run `run_id=probes-20260916T090344Z` (80/86 sanctioned probes retrievable in 186.7 s; `coverage.csv`, `coverage_summary.json`). Persistent identifier: TBD.

[2] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 2 — Usage Rights and Monetization," 2026-09-16. Persistent identifier: TBD.

[3] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 3 — Residual Scrape Harness Addendum," 2026-09-16. Persistent identifier: TBD.

[4] Environment and Climate Change Canada / Meteorological Service of Canada, "GeoMet — OGC API," Government of Canada. [Online]. Available: https://api.weather.gc.ca . Accessed: 2026-09-16.

[5] Environment and Climate Change Canada, "MSC Datamart — Hydrometric real-time data," Government of Canada. [Online]. Available: https://dd.weather.gc.ca/hydrometric/ . Accessed: 2026-09-16.

[6] Water Survey of Canada / Environment and Climate Change Canada, "HYDAT — National Water Data Archive," Government of Canada. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/monitoring/survey/data-products-services/national-archive-hydat.html . Accessed: 2026-09-16.

[7] Environment and Climate Change Canada, "City Page Weather (Datamart citypage_weather)," Government of Canada. [Online]. Available: https://dd.weather.gc.ca/citypage_weather/ . Accessed: 2026-09-16.

[8] Environment and Climate Change Canada, "Air Quality Health Index (AQHI)," Government of Canada. [Online]. Available: https://weather.gc.ca/airquality/pages/index_e.html . Accessed: 2026-09-16.

[9] Water Survey of Canada, "Hydrometric station drainage basin polygons (WSC gauge basins)," Government of Canada. [Online]. Available: https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/ . Accessed: 2026-09-16.

[10] Open-Meteo, "Open-Meteo Weather and Air-Quality APIs," Open-Meteo.com. [Online]. Available: https://open-meteo.com . Accessed: 2026-09-16.

[11] MET Norway, "Locationforecast API (api.met.no)," Norwegian Meteorological Institute. [Online]. Available: https://api.met.no/weatherapi/locationforecast/2.0/documentation . Accessed: 2026-09-16.

[12] Ontario Ministry of Natural Resources — Surface Water Monitoring Centre, "KiWIS (KISTERS Web Interoperability Solution) API." [Online]. Available: https://www.ontario.ca/page/surface-water-monitoring . Accessed: 2026-09-16.

[13] Province of British Columbia, "BC data — River Forecast Centre / Aquarius Web Portal." [Online]. Available: https://catalogue.data.gov.bc.ca/ . Accessed: 2026-09-16.

[14] Gouvernement du Québec, "Vigilance — Surveillance de la crue des rivières (WFS)." [Online]. Available: https://www.cehq.gouv.qc.ca/ . Accessed: 2026-09-16.

[15] Geological Survey of Canada / Groundwater Information Network, "GIN OGC Web Services and SensorThings API." [Online]. Available: https://gin.gw-info.net/ . Accessed: 2026-09-16.

[16] DataStream, "DataStream OData v4 API (RivTemp datasets)." [Online]. Available: https://datastream.org/ . Accessed: 2026-09-16.

[17] Canadian Integrated Ocean Observing System (CIOOS) Atlantic, "ERDDAP data server." [Online]. Available: https://cioosatlantic.ca/erddap/ . Accessed: 2026-09-16.

[18] V. Vionnet et al., "CanSWE — Canadian historical Snow Water Equivalent dataset," Zenodo. [Online]. Available: https://doi.org/10.5281/zenodo.10835278 . Accessed: 2026-09-16.

[19] Province of British Columbia, "Automated Snow Weather Stations (ASWS) near-real-time SWE." [Online]. Available: https://catalogue.data.gov.bc.ca/ . Accessed: 2026-09-16.

[20] Environment and Climate Change Canada, "Canadian River Ice Database (CRID)," Government of Canada. [Online]. Available: https://open.canada.ca/ . Accessed: 2026-09-16.

[21] B. Lehner et al., "HydroSHEDS / HydroBASINS," World Wildlife Fund. [Online]. Available: https://www.hydrosheds.org/ . Accessed: 2026-09-16.

[22] Province of Manitoba, "FloodInfo (ArcGIS Online) and Hydrologic Forecast Centre; OpenMB Information and Data Use Licence." [Online]. Available: https://www.gov.mb.ca/flooding/ . Accessed: 2026-09-16.

[23] Government of Newfoundland and Labrador, "Automated Data Reporting System (ADRS) — real-time hydrometric data." [Online]. Available: https://www.gov.nl.ca/ecc/waterres/ . Accessed: 2026-09-16.

[24] S. Bradner, "Key words for use in RFCs to Indicate Requirement Levels," RFC 2119, IETF, March 1997. [Online]. Available: https://www.rfc-editor.org/rfc/rfc2119 . Accessed: 2026-09-16.

[25] Open Geospatial Consortium, "OGC API — Features, OGC SensorThings API, and Web Feature Service (WFS) standards." [Online]. Available: https://www.ogc.org/standards/ . Accessed: 2026-09-16.

[26] Government of Canada, "Open Government Licence – Canada, version 2.0." [Online]. Available: https://open.canada.ca/en/open-government-licence-canada . Accessed: 2026-09-16.
