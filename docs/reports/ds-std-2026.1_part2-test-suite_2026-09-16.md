# WaterPulse Data-Source Standard (DS-STD-2026.1) — Part 2: Methodology & Test Suite

| Field | Value |
|---|---|
| **Report ID** | DS-STD-2026.1 |
| **Part** | 2 of 3 — Methodology & Test Suite |
| **Version** | 1.0 |
| **Status** | Draft |
| **Publication date** | 2026-09-16 |
| **Prepared for** | WaterPulse-Canada |
| **Authoring organization** | WaterPulse Data Engineering |
| **Persistent identifier** | TBD (placeholder) |
| **How to cite** | WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 2," 2026-09-16. |

---

## Abstract

This Part specifies the *measurement methodology* behind the WaterPulse Data-Source
Standard: how each candidate river-data source is exercised, what evidence every
test is required to emit, and how outcomes are classified into a canonical
failure-reason taxonomy. The methodology is realized as an executable suite of **90
probes** (86 sanctioned + 4 residual) organized across **12 data categories**, driven
by two runners: a polite, sequential *sanctioned* runner (`probe_sources`) that
verifies bulk/API/archive endpoints once per invocation, and a gentle, checkpointed
*residual* knee-finder (`stress_test`) that characterizes the safe sustainable request
rate for the handful of scrape-only sources. Every probe records **per-request** and
**per-test** evidence — never a bare pass/fail — capturing retrievability, field
inventory, maximum historical depth, record/station counts, latency, licence,
commercial-use posture, and a classified failure reason. This document defines the
shared probe contract, the auto-discovery registry, the classifier taxonomy, the
good-citizen (anti-flag) design constraints, the exact invocation commands, the full
enumeration of all 90 probes, and the on-disk evidence artifacts. It closes with the
known limitations of the method. The catalogue of *what each source is* and the
normative coverage matrix are the subject of Part 1 and are not restated here; the
dated results of the overnight residual run are the subject of Part 3.

**Index Terms** — data-source verification, hydrometric data, retrievability testing,
field inventory, failure classification, rate-limit characterization, open government
licensing, reproducible measurement, Canada, Environment and Climate Change Canada
(ECCC), Water Survey of Canada (WSC).

---

## 1. Scope and conformance language

### 1.1 Scope

This Part is the methodology specification for DS-STD-2026.1. It is normative with
respect to *how a WaterPulse source probe is written, run, and evidenced*. It is
descriptive with respect to source identity, jurisdictional architecture, and the
usage-rights matrix, all of which are specified in Part 1 [1]. The measured results
summarized herein derive from a single reference execution, run
`probes-20260916T090344Z` (2026-09-16), in which **80 of 86** sanctioned probes were
retrievable in **186.7 s** of wall-clock time; interpretation of the six non-OK
outcomes is deferred to Part 1 and Part 3.

### 1.2 Conformance language

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this
document are to be interpreted as described in RFC 2119 [2] as updated by RFC 8174 [3],
and appear in uppercase only when normative.

### 1.3 Relationship to other Parts

- **Part 1 — Catalogue & Coverage Matrix** [1]: the authoritative per-source detail,
  the 13-jurisdiction primary/backup architecture, and the usage-rights/monetization
  matrix. Where this Part names a `source_id`, its full description lives in Part 1.
- **Part 3 — Residual Overnight Addendum**: the dated results of the user-launched
  `stress_test` overnight run (safe-max concurrency and failure signatures per scrape
  target). Part 3 consumes the artifacts defined in §8 of this Part.

---

## 2. Objectives — what every test measures

The suite exists to answer, per source and with reproducible evidence, a fixed set of
questions. Each objective below is a first-class field on the per-test record (§8), not
a derived judgement.

1. **Retrievability.** Can the source be reached and a usable sample obtained *now*,
   from a neutral client, under polite load? Recorded as the boolean `retrievable`,
   decided by the probe itself (not inferred solely from HTTP status).
2. **Field inventory.** Which fields does the payload actually expose? Recorded as
   `fields_found` (a list) and `n_fields` (its length), discovered from the returned
   CSV header, JSON keys, or GeoJSON feature properties — the *measured* contract, not
   the advertised one.
3. **Maximum historical depth.** For archival sources, the earliest and latest years
   present in the sample and their span, recorded as `earliest_year`, `latest_year`,
   `span_years`.
4. **Coverage.** Record and station counts observed in the sample (`record_count`,
   `station_count`), the basis for the coverage rollup.
5. **Cadence / latency.** Per-request round-trip time (`latency_ms`) for every attempt,
   plus the retrieval latency attributed to the test.
6. **Licence & commercial posture.** The upstream `licence` and a `commercial_ok`
   disposition (`yes` / `no-written-permission` / `non-commercial` / `conditional` /
   `unknown`) carried as fixed metadata on every probe.
7. **Failure reason.** When a request or test does not succeed, a canonical
   `reason_category` (§4) that distinguishes *why* — a wrong address, a wrong station,
   a throttle, an upstream gap, a DNS failure, a missing key, and so on.

**Normative evidence requirement.** Every test **SHALL** emit its full evidence: one
row per HTTP attempt in `requests.csv` *and* a complete per-test JSON document. A probe
**SHALL NOT** reduce its output to a pass/fail verdict alone. A probe **SHOULD** attach
a trimmed raw response `sample` (evidence of the payload shape) and **SHOULD** keep that
sample bounded (on the order of the first several hundred bytes).

---

## 3. Architecture of the suite

### 3.1 Two runners, one contract

The suite is deliberately split into two runners that share one probe contract and one
HTTP client, but differ in load discipline and cadence:

| | `probe_sources` (sanctioned) | `stress_test` (residual) |
|---|---|---|
| **Module** | `tests/probe_sources.py` | `tests/stress_test.py` |
| **Population** | the 86 `sanctioned=True` probes | the 4 scrape-only targets (AB, SK, BC + an Open-Meteo burst) |
| **Load discipline** | one probe at a time, sequential, one bulk file / one API page / one SQLite read per source | graduated concurrency "bunches" with 10–30 min random gaps |
| **Cadence** | run once, on demand (CI-safe) | manual, overnight, ~10 h cap, checkpointed |
| **Goal** | retrievability + inventory + depth + coverage | safe-max sustainable rate + failure signatures (the "knee") |
| **Launch** | anyone, anytime | the user, ideally off a non-production IP |

Sanctioned probes are safe to run repeatedly and are the backbone of the coverage
evidence. Residual probes touch sources with **no** sanctioned bulk/API surface — where
the only access is scraping a page or polling an undocumented export — and therefore
**SHALL** be excluded from the default run and exercised only through the gentle
residual harness (or, once, via an explicit `--include-residual` flag on the sanctioned
runner).

### 3.2 The shared probe contract (`tests/sources/_base.py`)

A *source module* under `tests/sources/` registers one or more probes with the
`@register(...)` decorator (or by calling `register(...)` in a loop, for per-jurisdiction
families). Each probe is an `async def fn(spec, ctx) -> TestResult` that:

1. fetches a small, sanctioned sample from the source;
2. records **every** HTTP attempt via `http_probe(...)`;
3. inventories the fields, counts, and historical depth of what came back; and
4. returns `spec.result(retrievable=…, reason_category=…, …)`.

The contract's moving parts:

- **`ProbeSpec`** — the immutable registration record: `test_id`, `category`,
  `source_id`, `label`, `jurisdiction`, `licence`, `commercial_ok`, `sanctioned`, and
  the probe function. Its `.result(...)` helper stamps every returned `TestResult` with
  this metadata so a probe body cannot accidentally mislabel itself.
- **`ProbeContext`** — the runtime context handed to every probe: the `ResultLog`, the
  `run_id`, a `sample_size` (stations/records to sample where applicable, default 3), a
  `request_timeout` (default 60 s), a `cache_dir` for large downloads (HYDAT SQLite,
  CanSWE), and an `allow_downloads` gate for multi-megabyte fetches.
- **`http_probe(...)`** — the single instrumented HTTP entry point. It performs one
  attempt, times it, classifies the outcome, and returns a `Fetch` wrapping a
  `RequestRecord`. It **never raises** for HTTP or transport errors — it classifies them
  — so a probe can always make a decision and always emits a request row. A
  `from_metadata=True` flag marks URLs the *upstream advertised*, so that a 404 on such a
  URL is recorded as an upstream data gap rather than a client-side path bug (§4).
- **`ResultLog`** — the append-only writer that persists request rows, the per-test
  summary row, the coverage row, and the per-test JSON (§8).
- **Field-inventory helpers** — `fields_from_csv`, `fields_from_json` (dict / list-of-
  dict / GeoJSON `features[].properties` / OGC `value[]`), and `year_span` for depth.

**Normative contract rules.** A probe **SHALL** route every network attempt through
`http_probe(...)` so that no request escapes the evidence log. A probe **SHALL** be
read-only and low-load. A probe **SHOULD NOT** raise; if it does, the runner catches it,
classifies it, and records a `parse_error`/`unknown` result rather than aborting the run
(§3.4). A scrape-touchy or undocumented source **SHALL** be registered
`sanctioned=False`.

### 3.3 Auto-discovery registry (`tests/matrix.py`)

The matrix is a declarative registry with no hand-maintained list. `load_all()` walks
every module in `tests/sources/` (skipping `_`-prefixed private modules), imports each so
its `@register(...)` decorators and registration loops populate the shared `REGISTRY`,
and returns the list of `ProbeSpec`. **Adding a source is a one-file operation**: drop a
new `tests/sources/<name>.py`; no edit to the matrix or the runners is required.
`summarize()` produces the counts by category and the sanctioned/residual split used in
§7 and in the run summary.

### 3.4 The sanctioned runner (`tests/probe_sources.py`)

`probe_sources` loads the matrix, filters it (§6), sorts probes deterministically by
`(category, source_id, test_id)`, mints a `run_id` of the form `probes-<UTC-timestamp>`,
and executes each probe **sequentially**. Each probe is wrapped in `_run_one`, which
guarantees a crashing probe cannot bring down the run: an unhandled exception is
classified (`parse_error` if otherwise `unknown`) and recorded as a non-retrievable
result with the traceback detail. After the run it writes a machine-readable
`coverage_summary.json` (elapsed, totals, the matrix summary, counts by reason, counts
of retrievable per category, and commercial-posture counts).

### 3.5 The residual harness (`tests/stress_test.py` + `tests/stress/`)

The residual harness is a graduated **knee-finder**. It is described in §5.3; its target
registry, ladder, and gap policy live in `tests/stress/config.py`, its scheduling and
abort logic in `tests/stress/runner.py`, and its evidence writer in
`tests/stress/report.py`. It reuses the same `http_probe`, `build_client`, and
`RequestRecord` as the sanctioned runner, so a residual request is evidenced identically
to a sanctioned one.

---

## 4. The failure-reason classifier taxonomy

The classifier (`tests/stress/classify.py`) is the forensic core of the standard: it
maps an HTTP status or a transport/parse exception to exactly one canonical reason so
that Part 1 and Part 3 can catalogue *why* a source succeeds or fails rather than merely
*that* it did. Two success reasons and one deliberately-preserved distinction do most of
the interpretive work.

### 4.1 Categories

| Reason category | Distinguishes | Trigger |
|---|---|---|
| `ok` | usable data returned | 2xx with parseable, non-empty payload |
| `ok_empty` | reachable but nothing there | 2xx with zero records / no file link — a "needs a deeper query" signal, not a failure of the endpoint |
| `http_404_upstream_missing` | an *upstream* data gap | 404 on a URL the upstream **advertised** (`from_metadata=True`) |
| `http_404_bad_path` | *our* address mistake | 404 on a URL we **constructed** |
| `http_400_bad_request` | malformed query on our side | HTTP 400 |
| `http_401_unauthorized` | missing/invalid credential | HTTP 401 — e.g. an API key is required, not that the endpoint is down |
| `http_403_forbidden` | blocked / bot-protected | HTTP 403 (also treated as a throttle/block signal) |
| `http_429_rate_limited` | throttled | HTTP 429 |
| `http_5xx_server` | upstream server fault | HTTP 500–599 (throttle signal) |
| `http_other_status` | uncategorized status | any other non-2xx |
| `connect_refused` | host up-stack refuses / unreachable | `ConnectError` without a DNS hint ("All connection attempts failed") |
| `connect_timeout` | no handshake in time | `ConnectTimeout` |
| `read_timeout` | connected but no response body in time | `ReadTimeout` / `WriteTimeout` / `PoolTimeout` / generic `TimeoutException` |
| `dns_error` | name does not resolve | `ConnectError` whose message matches a DNS hint (`getaddrinfo`, "name or service not known", …) |
| `tls_error` | certificate / TLS failure | exception message mentions certificate / SSL / TLS |
| `invalid_station` | valid URL shape, bogus station id | station id absent from the source's list (probe-level determination) |
| `parse_error` | bytes returned but unreadable | `ValueError` / `KeyError` / `TypeError` during parse |
| `unknown` | unclassified | any residual `HTTPError` or other exception |

### 4.2 Why the distinctions matter

- **`ok` vs `ok_empty`.** A reachable endpoint that returns no rows is a materially
  different finding from a broken one. In the reference run, `ok_empty` cleanly labels
  the ECCC water-prediction collections and two ice databases as *retrievable but
  needing a deeper query* rather than as failures.
- **`http_404_upstream_missing` vs `http_404_bad_path`.** This is the single most
  important discrimination in the taxonomy and is why `http_probe` carries a
  `from_metadata` flag. A 404 on a URL the upstream itself published is an availability
  finding about the upstream; a 404 on a URL we built is our bug. Conflating them would
  make the standard blame the wrong party.
- **`dns_error` vs `connect_refused` vs `connect_timeout`.** These separate "the name
  does not resolve" (a catalogue/DNS problem, e.g. the federal groundwater SensorThings
  host) from "the host actively refuses" (e.g. intermittent Alberta refusal) from "the
  host never answered the handshake". A short connect timeout (§5) surfaces the refusal
  and timeout cases quickly instead of hanging on the full read timeout.
- **`http_401_unauthorized` vs a hard failure.** A 401 means a documented credential is
  required (e.g. the DataStream API key). The endpoint works; the probe simply lacks a
  key. Labeling it `http_401` prevents it from being mistaken for an outage.
- **`invalid_station`.** A syntactically valid request for a station the source does not
  carry is distinct from a broken request; it is a coverage fact about the source.

### 4.3 Derived reason sets

Two named sets steer the residual knee-finder and the abort logic:

- **`SUCCESS_REASONS = {ok, ok_empty}`** — reasons that count as a successful contact.
- **`THROTTLE_REASONS = {connect_refused, connect_timeout, read_timeout, http_429,
  http_5xx, http_403}`** — reasons interpreted as throttling/blocking; when their rate in
  a ladder step crosses the knee threshold, that target's ladder stops (§5.3).

---

## 5. Good-citizen / anti-flag design

The suite is engineered to be indistinguishable from a legitimate, well-behaved client
and to stay comfortably inside every upstream's acceptable-use posture. These are design
constraints, not optional niceties.

### 5.1 Identification and transport (`tests/stress/http_client.py`)

- **Descriptive, contactable User-Agent.** Every request carries
  `WaterPulse-Canada/1.0 (public-good hydrometric data-source diagnostic; contact:
  justin.jabrica@shaw.ca)`. The MSC Open Data usage policy [4] asks for a meaningful
  User-Agent; the MET Norway Terms of Service [6] *require* an identifying UA with
  contact information. A probe **SHALL** send this UA.
- **Bounded connection pool.** The shared client caps `max_connections` (default 8;
  residual bunches size the pool to the bunch's concurrency) to avoid socket churn that
  reads as abusive.
- **No cache-bypass headers.** The client **SHALL NOT** send `Cache-Control: no-cache`
  or equivalent bypass headers; the MSC policy forbids cache-bypass, and honoring caches
  reduces upstream load.
- **Redirect-following.** Several government hosts 30x to canonical URLs; the client
  follows redirects so a redirect is not miscounted as a failure.
- **Short connect timeout.** The connect timeout is capped (min(15 s, timeout)) so that
  `connect_refused` / `connect_timeout` surface quickly rather than blocking on the full
  read timeout — important for characterizing Alberta's intermittent refusal.

### 5.2 Sanctioned vs residual split

The single most important anti-flag decision is *what not to run by default*. Sources
with a bulk file, an OGC/REST API, or a downloadable archive are sanctioned and cost the
upstream one small request per probe. Sources with no such surface — where WaterPulse
would otherwise have to scrape or poll — are marked `sanctioned=False`, excluded from the
default run, and reachable only through the gentle residual harness. This keeps casual,
repeatable runs (including CI) off the fragile endpoints entirely.

### 5.3 Residual gentleness (the knee-finder)

When the residual harness does run, it is gentle by construction:

- **Graduated ladder.** Concurrency ramps over a small ladder (default `[1, 2, 4, 8,
  16]`, each capped per target) against one target at a time. Each `(target,
  concurrency)` step is one **bunch**.
- **Random long gaps.** Between bunches the harness sleeps a uniform random **10–30 min**
  (`gap_min_s`/`gap_max_s`); smoke mode collapses this to ~1–3 s for machinery
  validation only.
- **Stop at the knee.** After each ladder bunch the harness computes the throttle rate
  over `THROTTLE_REASONS`; once it crosses `knee_error_rate` (default 10 %) that target's
  ladder stops and the last clean level is recorded as its safe-max. Alberta is capped
  low deliberately.
- **Labelled bad-input probes.** Each target also runs an `invalid`-station bunch (valid
  URL shape, bogus id → expected `invalid_station`/upstream gap), a `badpath` bunch (a
  deliberately-malformed URL → our-mistake signature), and — for Open-Meteo only — a
  single `rapidburst` bunch (25 requests, no jitter) to capture the "requested too fast"
  signature. These give the failure taxonomy real, labelled examples.
- **Canary + abort.** If a bunch is ≥ 90 % blocked (`abort_block_rate` over
  `connect_refused`/`http_403`), the harness waits a full gap and fires a single-request
  canary; if the canary is also blocked it **aborts the whole run**. It never hammers a
  host that is pushing back.
- **Honors back-pressure.** `Retry-After` is parsed off every response into the request
  record; per-request start jitter (50–250 ms) desynchronizes a bunch; a ~10 h wall cap
  bounds the run; and every step is checkpointed for `--resume`.

The 2026-09-16 smoke validation confirmed the machinery: the weather ladder reached its
smoke safe-max at concurrency 4 with the rapid-burst probe (25 → smoke 5) showing no
throttle at low concurrency, and Alberta responded intermittently (its bad-path bunch
returning the expected 404). The full overnight run is the user's to launch; its results
become the Part 3 dated addendum.

---

## 6. How to run

All commands run inside the backend container. The sanctioned runner is safe to run at
any time; the residual harness is a manual, user-launched activity.

### 6.1 Sanctioned probes (`probe_sources`)

```bash
# Full sanctioned matrix (residual probes skipped)
docker-compose run --rm -w /app backend python -m tests.probe_sources

# One category only
docker-compose run --rm -w /app backend python -m tests.probe_sources --category historical

# One source only
docker-compose run --rm -w /app backend python -m tests.probe_sources --source SRC-HYDAT

# Specific probes by test_id (comma-separated)
docker-compose run --rm -w /app backend python -m tests.probe_sources --only current-eccc-datamart-on,stations-on-kiwis

# Skip the multi-MB downloads (HYDAT, CanSWE)
docker-compose run --rm -w /app backend python -m tests.probe_sources --no-downloads

# Also run the scrape/residual probes ONCE (normally harness-only)
docker-compose run --rm -w /app backend python -m tests.probe_sources --include-residual
```

Sanctioned-runner flags: `--category`, `--source`, `--only`, `--include-residual`,
`--no-downloads`, `--timeout` (default 60 s), `--sample-size` (default 3), `--cache-dir`,
`--logs-dir`.

### 6.2 Residual gentle harness (`stress_test`)

Run this yourself, ideally from a non-production IP, and pause the app's 10-minute
scheduler first.

```bash
# Validate the machinery fast (tiny ladder, ~2 s gaps)
docker compose run --rm -T --no-deps --entrypoint python backend \
    -m tests.stress_test --smoke

# The real overnight run (detached; runs for hours)
docker compose run -d --name wp-stress --no-deps --entrypoint python backend \
    -m tests.stress_test --targets ab,sk,bc,weather --max-hours 10

# Stop early (checkpoint + partial CSVs are already on disk)
docker stop wp-stress

# Resume after the last checkpoint (pass the run_id printed at start)
docker compose run --rm -T --no-deps --entrypoint python backend \
    -m tests.stress_test --resume <run_id>
```

Residual-harness flags: `--targets` (subset of `ab,sk,bc,weather`), `--smoke`,
`--max-hours` (default 10), `--gap-min`/`--gap-max` (default 600/1800 s), `--timeout`
(default 45 s), `--seed` (default 1234), `--resume <run_id>`, `--logs-dir`.

---

## 7. Full test enumeration

The tables below enumerate **all 90 probes** in the registry, grouped by category. The
**Sanct.** column is the `sanctioned` flag (`yes` = in the default `probe_sources` run;
`no` = residual, harness-only). The **Comm.** column is the `commercial_ok` disposition.
Per-source detail is in Part 1 [1]; this is the test-level index, not the catalogue.

**Registry totals** (from `matrix.summarize()`): **90 probes = 86 sanctioned + 4
residual**, across 12 categories — aqi 2, current 20, stations 15, historical 19,
drainage 6, groundwater 6, flood 6, precip 4, ice 3, snow 3, weather 4, watertemp 2.

> Note on the residual set. The four `sanctioned=False` registry probes are
> `current-ab-rivers` (SRC-AB-RIVERS), `current-bc-aquarius` (SRC-BC-AQUARIUS),
> `current-sk-wsa` (SRC-SK-WSA), and `snow-ab-pillows-residual` (SRC-AB-SNOW). The
> residual *stress harness* (§5.3) drives a slightly different set — its four targets are
> `ab`, `sk`, `bc`, and a `weather` (Open-Meteo) rapid-burst target — because the
> Open-Meteo burst characterizes a rate signature rather than registering a source probe.

### 7.1 aqi — 2 probes (2 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `aqi-eccc-aqhi-ca` | ECCC AQHI observations (GeoMet OGC API) | SRC-ECCC-AQHI | CA | yes | OGL-Canada / MSC GeoMet | yes |
| `aqi-open-meteo-aqi` | Open-Meteo Air Quality (us_aqi + pm2.5/pm10) | SRC-OPEN-METEO-AQI | multi | yes | CC-BY-4.0 | non-commercial |

### 7.2 current — 20 probes (17 sanctioned + 3 residual)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `current-eccc-datamart-ab` | Datamart hourly bulk CSV (AB) | SRC-ECCC-DATAMART | AB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-bc` | Datamart hourly bulk CSV (BC) | SRC-ECCC-DATAMART | BC | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-mb` | Datamart hourly bulk CSV (MB) | SRC-ECCC-DATAMART | MB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-nb` | Datamart hourly bulk CSV (NB) | SRC-ECCC-DATAMART | NB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-nl` | Datamart hourly bulk CSV (NL) | SRC-ECCC-DATAMART | NL | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-ns` | Datamart hourly bulk CSV (NS) | SRC-ECCC-DATAMART | NS | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-nt` | Datamart hourly bulk CSV (NT) | SRC-ECCC-DATAMART | NT | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-nu` | Datamart hourly bulk CSV (NU) | SRC-ECCC-DATAMART | NU | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-on` | Datamart hourly bulk CSV (ON) | SRC-ECCC-DATAMART | ON | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-pe` | Datamart hourly bulk CSV (PE) | SRC-ECCC-DATAMART | PE | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-qc` | Datamart hourly bulk CSV (QC) | SRC-ECCC-DATAMART | QC | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-sk` | Datamart hourly bulk CSV (SK) | SRC-ECCC-DATAMART | SK | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-datamart-yt` | Datamart hourly bulk CSV (YT) | SRC-ECCC-DATAMART | YT | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `current-eccc-geomet-ca` | GeoMet OGC API hydrometric-realtime (national sample) | SRC-ECCC-GEOMET | CA | yes | OGL-Canada / MSC v2.1.1 | yes |
| `current-mb-floodinfo` | Manitoba FloodInfo AGOL CSV (level/flow/forecast) | SRC-MB-FLOODINFO | MB | yes | OpenMB | yes |
| `current-nl-adrs` | NL ADRS per-station CSV (level/flow/temp) | SRC-NL-ADRS | NL | yes | OGL-NL | yes |
| `current-qc-vigilance` | Québec Vigilance WFS stations (GeoJSON) | SRC-QC-VIGILANCE | QC | yes | CC-BY-4.0 (QC) | yes |
| `current-ab-rivers` | Alberta River Basins ListStationsAndAlerts (discovery) | SRC-AB-RIVERS | AB | **no** | GoA copyright | non-commercial |
| `current-bc-aquarius` | BC ENV AQUARIUS WebPortal export (undocumented) | SRC-BC-AQUARIUS | BC | **no** | OGL-BC | yes |
| `current-sk-wsa` | Saskatchewan WSA hydrograph (dygraphs htmlwidget, scrape) | SRC-SK-WSA | SK | **no** | SK Crown copyright | no-written-permission |

### 7.3 stations — 15 probes (15 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `stations-eccc-climate-stations` | GeoMet climate-stations (station metadata) | SRC-ECCC-CLIMATE | CA | yes | OGL-Canada | yes |
| `stations-eccc-geomet-ab` | GeoMet OGC API hydrometric stations (AB) | SRC-ECCC-GEOMET | AB | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-bc` | GeoMet OGC API hydrometric stations (BC) | SRC-ECCC-GEOMET | BC | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-mb` | GeoMet OGC API hydrometric stations (MB) | SRC-ECCC-GEOMET | MB | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-nb` | GeoMet OGC API hydrometric stations (NB) | SRC-ECCC-GEOMET | NB | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-nl` | GeoMet OGC API hydrometric stations (NL) | SRC-ECCC-GEOMET | NL | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-ns` | GeoMet OGC API hydrometric stations (NS) | SRC-ECCC-GEOMET | NS | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-nt` | GeoMet OGC API hydrometric stations (NT) | SRC-ECCC-GEOMET | NT | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-nu` | GeoMet OGC API hydrometric stations (NU) | SRC-ECCC-GEOMET | NU | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-on` | GeoMet OGC API hydrometric stations (ON) | SRC-ECCC-GEOMET | ON | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-pe` | GeoMet OGC API hydrometric stations (PE) | SRC-ECCC-GEOMET | PE | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-qc` | GeoMet OGC API hydrometric stations (QC) | SRC-ECCC-GEOMET | QC | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-sk` | GeoMet OGC API hydrometric stations (SK) | SRC-ECCC-GEOMET | SK | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-eccc-geomet-yt` | GeoMet OGC API hydrometric stations (YT) | SRC-ECCC-GEOMET | YT | yes | OGL-Canada / MSC v2.1.1 | yes |
| `stations-on-kiwis` | Ontario SWMC KiWIS getStationList (JSON) | SRC-ON-KIWIS | ON | yes | OGL-Ontario | yes |

### 7.4 historical — 19 probes (19 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `historical-hydat-ca` | HYDAT national archive (daily/monthly means, full record) | SRC-HYDAT | CA | yes | OGL-Canada / ECCC | yes |
| `historical-eccc-geomet-annual-peaks` | GeoMet OGC API hydrometric-annual-peaks (05BB001) | SRC-ECCC-GEOMET | CA | yes | OGL-Canada / MSC v2.1.1 | yes |
| `historical-eccc-geomet-annual-statistics` | GeoMet OGC API hydrometric-annual-statistics (05BB001) | SRC-ECCC-GEOMET | CA | yes | OGL-Canada / MSC v2.1.1 | yes |
| `historical-eccc-geomet-daily-mean` | GeoMet OGC API hydrometric-daily-mean (05BB001) | SRC-ECCC-GEOMET | CA | yes | OGL-Canada / MSC v2.1.1 | yes |
| `historical-eccc-geomet-monthly-mean` | GeoMet OGC API hydrometric-monthly-mean (05BB001) | SRC-ECCC-GEOMET | CA | yes | OGL-Canada / MSC v2.1.1 | yes |
| `historical-bypt-ab` | ECCC daily-mean historical depth (AB) | SRC-ECCC-GEOMET-DAILY | AB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-bc` | ECCC daily-mean historical depth (BC) | SRC-ECCC-GEOMET-DAILY | BC | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-mb` | ECCC daily-mean historical depth (MB) | SRC-ECCC-GEOMET-DAILY | MB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-nb` | ECCC daily-mean historical depth (NB) | SRC-ECCC-GEOMET-DAILY | NB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-nl` | ECCC daily-mean historical depth (NL) | SRC-ECCC-GEOMET-DAILY | NL | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-ns` | ECCC daily-mean historical depth (NS) | SRC-ECCC-GEOMET-DAILY | NS | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-nt` | ECCC daily-mean historical depth (NT) | SRC-ECCC-GEOMET-DAILY | NT | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-nu` | ECCC daily-mean historical depth (NU) | SRC-ECCC-GEOMET-DAILY | NU | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-on` | ECCC daily-mean historical depth (ON) | SRC-ECCC-GEOMET-DAILY | ON | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-pe` | ECCC daily-mean historical depth (PE) | SRC-ECCC-GEOMET-DAILY | PE | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-qc` | ECCC daily-mean historical depth (QC) | SRC-ECCC-GEOMET-DAILY | QC | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-sk` | ECCC daily-mean historical depth (SK) | SRC-ECCC-GEOMET-DAILY | SK | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-bypt-yt` | ECCC daily-mean historical depth (YT) | SRC-ECCC-GEOMET-DAILY | YT | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `historical-weather-openmeteo-archive` | Open-Meteo Archive (ERA5) historical daily weather | SRC-OPEN-METEO-ARCHIVE | multi | yes | CC-BY-4.0 | non-commercial |

### 7.5 drainage — 6 probes (6 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `drainage-hydrosheds-hydrobasins` | HydroSHEDS HydroBASINS nested watershed polygons | SRC-HYDROSHEDS | CA | yes | HydroSHEDS Licence | yes |
| `drainage-nhn-ca` | National Hydro Network (NHN) | SRC-NHN | CA | yes | OGL-Canada 2.0 | yes |
| `drainage-wsc-basins-ca` | WSC gauge drainage-basin polygons (national) | SRC-WSC-BASINS | CA | yes | OGL-Canada 2.0 | yes |
| `drainage-bc-fwa-bc` | BC Freshwater Atlas watershed boundaries | SRC-BC-FWA | BC | yes | OGL-BC 2.0 | yes |
| `drainage-on-oih-on` | Ontario Integrated Hydrology (OIH) data | SRC-ON-OIH | ON | yes | OGL-Ontario 1.0 | yes |
| `drainage-qc-grhq-qc` | QC GRHQ hydro network | SRC-QC-GRHQ | QC | yes | CC-BY-4.0 | yes |

### 7.6 groundwater — 6 probes (6 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `groundwater-gin-wms-ca` | GIN WMS GetCapabilities (national groundwater layers) | SRC-GIN | CA | yes | OGL-Canada | yes |
| `groundwater-sta-gw-ca` | GSC SensorThings groundwater (national Things) | SRC-STA-GW | CA | yes | OGL-Canada | yes |
| `groundwater-sta-gw-on` | GSC SensorThings groundwater (ON) | SRC-STA-GW | ON | yes | OGL-Canada | yes |
| `groundwater-sta-gw-qc` | GSC SensorThings groundwater (QC) | SRC-STA-GW | QC | yes | OGL-Canada | yes |
| `groundwater-on-pgmn` | Ontario PGMN (CKAN package_show) | SRC-ON-PGMN | ON | yes | OGL-Ontario | yes |
| `groundwater-qc-rsesq` | Québec RSESQ (Données Québec CKAN) | SRC-QC-RSESQ | QC | yes | CC-BY-4.0 | yes |

### 7.7 flood — 6 probes (6 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `flood-eccc-waterpred-ca` | ECCC GeoMet water-prediction collections (WCPS/OHPS/surge) | SRC-ECCC-WATERPRED | CA | yes | OGL-Canada / ECCC | yes |
| `flood-nrcan-fhimp-ca` | NRCan FHIMP flood-mapping hub (geo.ca) | SRC-NRCAN-FLOOD | CA | yes | OGL-Canada | yes |
| `flood-bc-rfc-notifications` | BC River Forecast Centre warnings (ArcGIS) | SRC-BC-RFC | BC | yes | OGL-BC | yes |
| `flood-mb-hfc` | Manitoba Hydrologic Forecast Centre (HTML/PDF) | SRC-MB-HFC | MB | yes | MB terms (unspecified) | unknown |
| `flood-on-conservation-ontario` | Conservation Ontario flood forecasting & warning (HTML/PDF) | SRC-ON-CO | ON | yes | CO terms (unspecified) | unknown |
| `flood-qc-vigilance` | Québec Vigilance flood-surveillance WFS | SRC-QC-VIGILANCE | QC | yes | CC-BY-4.0 (QC) | yes |

### 7.8 precip — 4 probes (4 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `precip-eccc-climate-daily` | GeoMet climate-daily (precip + snow-on-ground) | SRC-ECCC-CLIMATE | CA | yes | OGL-Canada | yes |
| `precip-eccc-climate-hourly` | GeoMet climate-hourly (hourly obs) | SRC-ECCC-CLIMATE | CA | yes | OGL-Canada | yes |
| `precip-eccc-climate-monthly` | GeoMet climate-monthly (monthly summaries) | SRC-ECCC-CLIMATE | CA | yes | OGL-Canada | yes |
| `precip-eccc-rdpa-capa-10km` | GeoMet RDPA/CaPA 10 km 6 h accumulation (collection metadata) | SRC-ECCC-CLIMATE | CA | yes | OGL-Canada | yes |

### 7.9 ice — 3 probes (3 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `ice-cis-thickness-ca` | Canadian Ice Service ice-thickness archive (data page) | SRC-CIS-ICE | CA | yes | OGL-Canada | yes |
| `ice-crid-ca` | Canadian River Ice Database (NHP sites, freeze/break-up) | SRC-CRID | CA | yes | OGL-Canada | yes |
| `ice-lakeice-ca` | Lake Ice Database (freeze-up / break-up / ice cover) | SRC-LAKEICE | CA | yes | OGL-Canada | yes |

### 7.10 snow — 3 probes (2 sanctioned + 1 residual)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `snow-canswe-zenodo-ca` | CanSWE national SWE dataset (Zenodo record metadata) | SRC-CANSWE | CA | yes | OGL-Canada (Zenodo) | yes |
| `snow-bc-asws-swe` | BC ASWS near-real-time SWE (wide CSV) | SRC-BC-ASWS | BC | yes | OGL-BC | yes |
| `snow-ab-pillows-residual` | Alberta River Basins snow pillows (residual) | SRC-AB-SNOW | AB | **no** | OGL-Alberta (unconfirmed) | unknown |

### 7.11 weather — 4 probes (4 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `weather-eccc-citypage-sitelist` | ECCC City Page — site catalogue CSV (all cities) | SRC-ECCC-CITYPAGE | CA | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `weather-eccc-citypage-ab` | ECCC City Page — city XML (Calgary, AB) | SRC-ECCC-CITYPAGE | AB | yes | OGL-Canada / ECCC v2.1.1 | yes |
| `weather-met-norway-locationforecast` | MET Norway Locationforecast 2.0 (compact point forecast) | SRC-MET-NORWAY | CA | yes | CC-BY-4.0 / NLOD-2.0 | yes |
| `weather-openmeteo-forecast-ca` | Open-Meteo forecast (current + 7-day; app weather contract) | SRC-OPEN-METEO | CA | yes | CC-BY-4.0 | non-commercial |

### 7.12 watertemp — 2 probes (2 sanctioned)

| Test ID | Label | Source ID | Juris. | Sanct. | Licence | Comm. |
|---|---|---|---|---|---|---|
| `watertemp-rivtemp-datastream-ca` | RivTemp river temperature via DataStream OData v4 API | SRC-RIVTEMP | CA | yes | DataStream per-dataset | conditional |
| `watertemp-cioos-erddap-multi` | CIOOS Atlantic ERDDAP catalogue (coastal water temp) | SRC-CIOOS | multi | yes | CC-BY / OGL / CC0 (per-dataset) | yes |

---

## 8. Evidence artifacts

Every run writes a self-contained evidence directory `tests/logs/<run_id>/`. Nothing is
pass/fail-only; the raw request rows and per-test JSON are always retained.

### 8.1 Sanctioned run (`probes-<UTC-timestamp>/`)

| Artifact | Grain | Columns / keys |
|---|---|---|
| `requests.csv` | one row per HTTP attempt | `ts_utc, source_id, category, method, url, http_status, outcome, reason_category, reason_detail, error_type, latency_ms, resp_bytes, records_parsed, retry_after_s, notes` |
| `tests.csv` | one row per probe (summary) | `test_id, category, source_id, label, jurisdiction, licence, commercial_ok, retrievable, reason_category, endpoint, n_fields, fields_found, record_count, station_count, earliest_year, latest_year, span_years, latency_ms, n_requests, reason_detail, notes` |
| `coverage.csv` | one row per probe (coverage rollup) | `category, source_id, label, jurisdiction, retrievable, reason_category, n_fields, record_count, station_count, earliest_year, span_years, latency_ms, commercial_ok, licence` |
| `tests/<test_id>.json` | full per-test document | the complete `TestResult` incl. `fields_found`, `sample`, and the probe's own `requests[]` rows |
| `coverage_summary.json` | run-level rollup | `run_id, elapsed_seconds, total, retrievable, failed, matrix{total,sanctioned,residual,by_category}, by_reason, by_category_retrievable, commercial_ok_counts` |

The `fields_found` list is stored `|`-joined in the CSV and as a JSON array in the
per-test document, so the *measured* field contract is machine-diffable across runs.

### 8.2 Residual run (`stress-<UTC-timestamp>/`)

| Artifact | Grain | Contents |
|---|---|---|
| `requests.csv` | one row per HTTP attempt | same schema as §8.1 (shared `RequestRecord`) |
| `bunches.csv` | one row per bunch | `bunch_id, ts_utc, target, kind, concurrency, n_req, n_ok, n_fail, success_rate, throughput_req_s, p50_ms, p95_ms, max_ms, reason_breakdown, knee, gap_after_s, notes` |
| `events.log` | timestamped timeline | start, per-bunch gaps and results, knee hits, block/canary/abort events, completion |
| `checkpoint.json` | resumable state | `run_id, processed, bunches_run, knee_hit[], safe_max{}, aborted` |
| `summary.json` / `summary.md` | run rollup | bunches, requests, elapsed, aborted, `safe_max` per target, `knee_hit`, and the failure-reason catalogue (`reason_totals`) |

The `bunches.csv` `kind` column labels each bunch (`ladder` / `invalid` / `badpath` /
`rapidburst`), and `reason_breakdown` is a JSON histogram of `reason_category` for that
bunch — the raw material for the Part 3 safe-max recommendation and failure-signature
catalogue.

---

## 9. Limitations of the method

1. **Point-in-time sampling.** Each sanctioned probe fetches one small sample. A source
   that is transiently up (or down) at run time is recorded as such; retrievability is a
   snapshot, not an SLA. Repeated runs over time are the intended mitigation, and every
   run is independently timestamped and retained.
2. **Sampled depth, not exhaustive depth.** `earliest_year`/`span_years` reflect the
   sample requested (e.g. a single representative WSC station such as 05BB001 for the
   GeoMet historical collections), not the deepest record in the entire archive. HYDAT is
   the exception: it reads the full national archive and therefore reports true maxima.
3. **Field inventory is best-effort.** `fields_from_json` handles dict / list-of-dict /
   GeoJSON / OGC `value[]` shapes; unusual envelopes may under-report fields. A field
   present only in some records but absent from the first sampled record can be missed.
4. **Classifier heuristics.** `dns_error` vs `connect_refused` and `tls_error` are
   inferred partly from exception message text, which is library- and platform-dependent;
   a future `httpx`/`anyio` change could reshuffle a small number of edge classifications.
   The `from_metadata` distinction is only as good as the probe author's honest marking of
   which URLs came from upstream metadata.
5. **`ok_empty` is under-specified by design.** It means "reachable, but this light query
   returned nothing." Whether that is a genuine empty result or an under-parameterized
   query requires a deeper follow-up query that is out of scope for a low-load probe.
6. **Residual results are environment-sensitive.** Safe-max concurrency and block
   signatures depend on the originating IP, time of day, and upstream state. A run from a
   production IP, or during upstream maintenance, will not generalize; Part 3 records the
   exact conditions of its run.
7. **Not a load test.** The suite is explicitly *gentle*. It characterizes the *onset* of
   throttling (the knee) at low concurrency; it does not, and must not, probe an upstream's
   true ceiling. Reported safe-max values are conservative lower bounds.
8. **Licence/commercial fields are asserted metadata.** `licence` and `commercial_ok` are
   carried on each probe from the analysis in Part 1; they are not re-derived from the
   response at run time and can drift if an upstream changes terms. They are a pointer to
   Part 1, not an independent legal determination.

---

## 10. References

[1] WaterPulse Data Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 1
— Catalogue & Coverage Matrix," 2026-09-16.

[2] S. Bradner, "Key words for use in RFCs to Indicate Requirement Levels," RFC 2119,
IETF, Mar. 1997. [Online]. Available: https://www.rfc-editor.org/rfc/rfc2119. Accessed:
2026-09-16.

[3] B. Leiba, "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words," RFC 8174,
IETF, May 2017. [Online]. Available: https://www.rfc-editor.org/rfc/rfc8174. Accessed:
2026-09-16.

[4] Environment and Climate Change Canada / Meteorological Service of Canada, "MSC Open
Data / GeoMet — usage and acceptable-use policy," Government of Canada. [Online].
Available: https://eccc-msc.github.io/open-data/msc-data/readme_en/. Accessed:
2026-09-16.

[5] Environment and Climate Change Canada, "MSC GeoMet — OGC API and web services,"
Government of Canada. [Online]. Available: https://api.weather.gc.ca/. Accessed:
2026-09-16.

[6] Norwegian Meteorological Institute (MET Norway), "API Terms of Service — identifying
User-Agent requirement," api.met.no. [Online]. Available: https://api.met.no/doc/TermsOfService.
Accessed: 2026-09-16.

[7] Open-Meteo, "Terms & API usage limits (free non-commercial tier)," open-meteo.com.
[Online]. Available: https://open-meteo.com/en/terms. Accessed: 2026-09-16.

[8] DataStream, "DataStream Public API (OData v4) — authentication and rate limits,"
datastream.org. [Online]. Available: https://datastream.org/. Accessed: 2026-09-16.

[9] Open Geospatial Consortium, "OGC API — Features / OGC API — EDR," OGC. [Online].
Available: https://ogcapi.ogc.org/. Accessed: 2026-09-16.

[10] Encode, "HTTPX — a next-generation HTTP client for Python (async)." [Online].
Available: https://www.python-httpx.org/. Accessed: 2026-09-16.

[11] Python Software Foundation, "asyncio — Asynchronous I/O," Python 3 documentation.
[Online]. Available: https://docs.python.org/3/library/asyncio.html. Accessed:
2026-09-16.

[12] Government of Canada, "Open Government Licence — Canada, v2.0." [Online]. Available:
https://open.canada.ca/en/open-government-licence-canada. Accessed: 2026-09-16.

---

*End of DS-STD-2026.1 Part 2 — Methodology & Test Suite. Cite as: WaterPulse Data
Engineering, "WaterPulse Data-Source Standard (DS-STD-2026.1), Part 2," 2026-09-16.
Persistent identifier: TBD (placeholder).*
