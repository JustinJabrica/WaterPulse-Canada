# WaterPulse — Data-Source Verification Suite (DS-STD-2026.1)

Read-only probes that verify **every Canadian hydrometric / weather / environmental data
source** WaterPulse uses or may use — plus a gentle residual harness for the few sources that
must be scraped. This suite produces the evidence behind the **WaterPulse Data-Source Standard
`DS-STD-2026.1`** (see `docs/reports/`).

## Purpose
- Confirm each source is **retrievable**, and inventory the **fields** it returns, its **max
  historical depth**, **station/spatial coverage**, **latency**, **licence**, and — on failure —
  a classified **reason** (wrong address vs invalid station vs throttled vs upstream-missing vs
  timeout). This is the forensic follow-up to the `ConnectError` incident on `rivers.alberta.ca`.
- Prefer each jurisdiction's **own authoritative source as PRIMARY**, with **ECCC/WSC as backup**
  (except QC, where ECCC carries only ~15 realtime stations, so QC is provincial-only).

## What's here
```
tests/
  matrix.py            # auto-discovers every sources/*.py and returns the probe registry
  probe_sources.py     # runs the SANCTIONED probes (safe, low-load) + writes evidence + coverage
  stress_test.py       # residual gentle harness for scrape sources (MANUAL launch only)
  sources/*.py         # one module per source; each @register(...)s its probes
  stress/              # shared harness internals (metrics/logging, classifier, HTTP client, runner)
  logs/                # run outputs (gitignored): requests.csv, tests.csv, coverage.csv, per-test JSON
```
Every test emits its **full evidence** — per-request rows in `logs/<run_id>/requests.csv`, a
summary row in `tests.csv`, and a per-test JSON in `logs/<run_id>/tests/`. No test is
pass/fail-only.

## How to run (inside the backend container — it has httpx + env)
```bash
# All sanctioned probes (safe to run anytime; ~one small request per source):
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources

# Narrow scope:
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources --category historical
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources --source SRC-HYDAT

# Skip multi-MB downloads (fast validation; HYDAT etc. report metadata-only):
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources --no-downloads

# Residual gentle harness (scrape/touchy sources; runs for hours) — YOU launch this:
docker compose run -d --name wp-stress --no-deps --entrypoint python backend -m tests.stress_test --targets ab,sk,bc --max-hours 10
```
Outputs appear on the host under `waterpulse-backend/tests/logs/<run_id>/` (bind-mounted).
Stop the residual run with `docker stop wp-stress`; resume with `--resume <run_id>`.

> Note: on Git Bash, prefix commands with `MSYS_NO_PATHCONV=1` so paths aren't mangled.
> The container's WORKDIR is `/app`, so `-w` is unnecessary. `--no-deps` skips starting the DB
> (the sanctioned probes don't need it).

## Reading the results
- `logs/<run_id>/coverage.csv` — one row per source: retrievable, #fields, record/station counts,
  earliest year, span, latency, licence, commercial-use.
- `logs/<run_id>/coverage_summary.json` — totals, counts by reason/category, commercial-use tally.
- `logs/<run_id>/tests/<test_id>.json` — full detail incl. every HTTP attempt + a raw sample.

## Legal / technical constraints (attribution strings the app must display)
- **ECCC / WSC** (Datamart, GeoMet, HYDAT, City Page, AQHI, climate): OGL-Canada / ECCC End-use
  Licence v2.1.1 — commercial OK — *"Data Source: Environment and Climate Change Canada."*
  Acceptable-use: contact MSC only above ~86,400 req/day (~1 req/s); **no cache-bypass headers**.
- **Alberta** (`rivers.alberta.ca`): Government of Alberta copyright — **non-commercial only**
  (commercial needs written permission); "authorized users only" gate; aggressively refuses
  connections. Attribute *"Government of Alberta."*
- **Saskatchewan** (WSA): Crown copyright — non-commercial OK, commercial needs permission.
- **Manitoba**: OpenMB — commercial OK — *"Contains information … OpenMB … (Manitoba.ca/OpenMB)."*
- **BC / ON / NB / NS / PE / NL / YT**: OGL-<jurisdiction> — commercial OK —
  *"Contains information licensed under the Open Government Licence – <jurisdiction>."*
- **Québec**: CC-BY 4.0 (Québec) — commercial OK — attribute *Gouvernement du Québec*.
- **MET Norway**: CC-BY / NLOD — commercial OK — *"Data from MET Norway"* (descriptive UA required).
- **Open-Meteo**: CC-BY 4.0 — **free tier non-commercial only** — *"Weather data by Open-Meteo.com."*
- **RivTemp / DataStream**: attribution + DOI; **API key required** (x-api-key, 2 req/s).
- **CIOOS**: CC-BY 4.0 / OGL-Canada / CC0 (per dataset).

## Safety (residual harness)
Runs from a single IP against live government servers. It is deliberately gentle: graduated
knee-finder (Alberta capped low), **random 10–30 min gaps** between bunches, descriptive
User-Agent with contact, honours `Retry-After`, no cache-bypass, ~10 h cap, and **aborts on
sustained blocking**. Prefer a **non-production IP** and pause the app's 10-min scheduler during
a run so it doesn't compound load. Bad-input probes (invalid station / bad path / one small
rapid burst) are labelled and target the most tolerant endpoint.
