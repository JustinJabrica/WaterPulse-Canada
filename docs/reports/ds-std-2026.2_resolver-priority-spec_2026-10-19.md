# WaterPulse — Source-Priority Resolver Spec (DS-STD-2026.2 companion)

**Status:** design only (ingestion-phase; not built this round) · **Date:** 2026-10-19
**Refines:** DS-STD-2026.1 implementation-spec §2 (`app/services/resolver.py`, R2.1–R2.5)

## 1. Problem

For a given physical gauge/area, many sources may carry the same data (a provincial
feed, ECCC Datamart, ECCC GeoMet, HYDAT …). We must decide, **per physical station and
per data type**, which source is PRIMARY — and the answer depends on three things that
pull in different directions:

- **Trust/locality** — you want the jurisdiction's own authoritative feed as primary
  (provincial/municipal), with ECCC/WSC as the reliable floor.
- **Freshness** — "most frequently updated" is a strong signal, now *measured* (the probe
  suite records `data_age_minutes` per real-time source).
- **Monetization/licensing** — ad-supported pages may only show commercial-OK sources;
  non-commercial sources (Open-Meteo free tier, AB portal, SK WSA) are restricted to
  ad-free surfaces. **Licensing never excludes a source from ingestion — only from a surface.**

Registration order (the 2026.1 `_merge_readings` approach) can't express this. The resolver
makes it **declarative, per-station, and evidence-driven.**

## 2. Shape

`app/services/resolver.py` exposing:

```
resolve(station, data_type, surface) -> list[source_id]   # ranked, best first
```

- **station** — a *physical* station (deduped across sources; see §6).
- **data_type** — `realtime_flow` | `realtime_level` | `history` | `water_quality` |
  `flood_warning` | `flood_forecast` | `weather` | `aqi` | `tide` | `smoke` | …
- **surface** — `ad_supported` | `ad_free` (the page context the data will render on).

Returns a ranked list (not a single id) so callers can fall through on live failure.

## 3. Resolution algorithm

**Step 1 — eligibility gate (hard filters; a source is dropped, not scored, if it fails):**
1. **Coverage** — the source actually carries this station + data_type.
2. **Surface licence** — if `surface == ad_supported`, keep only `commercial_ok ∈ {yes, conditional-and-commercial-OK}`; `ad_free` keeps everything.
3. **Health** — source is not in a tripped circuit-breaker state (recent sustained failures; e.g. AB's connection refusals).

**Step 2 — score each eligible source** (0–1 each, weighted sum):

| factor | meaning | source of truth |
|---|---|---|
| `authority` | official operator of this gauge; validated > provisional | static `SOURCE_PROFILE` |
| `freshness` | `data_age_minutes` normalized against the data_type's expected cadence | probe `coverage.csv` / live telemetry |
| `reliability` | recent success rate / uptime | probe history + residual harness + app fetch telemetry |
| `granularity` | sub-hourly > hourly > daily | static `SOURCE_PROFILE` |

```
score = 0.35*authority + 0.30*freshness + 0.25*reliability + 0.10*granularity
freshness = clamp(1 - data_age_minutes / (k * expected_cadence_minutes), 0, 1)   # k≈3
```
Weights/`k` are config, not code. Freshness is normalized *per data type* — a 6 h old daily
value isn't "stale," a 6 h old realtime value is.

**Step 3 — provincial-preferred tiebreak:** when top scores are within a small epsilon, add a
small bonus to provincial/municipal over federal (ECCC). This encodes "provincial primary,
ECCC floor" without letting a stale/flaky provincial feed beat a fresh reliable ECCC one.

**Step 4 — declarative overrides** (`JURISDICTION_POLICY`, highest precedence):
- **QC → provincial mandatory** for realtime (ECCC carries only ~15 QC realtime stations):
  Vigilance primary; ECCC not used for QC realtime.
- **AB, SK → non-commercial:** eligible only on `ad_free`; on `ad_supported` they're gated out
  by Step 1 and the resolver falls through to ECCC. AB additionally scores low on reliability
  (connection refusals) — so even ad-free it only wins when actually up.
- **Municipal → primary only for advisory/beach layers** (`flood_warning`, swim/beach WQ);
  elsewhere it's a supplement, not a primary.

## 4. Per-data-type policy (because "primary" differs by layer)

| data_type | policy |
|---|---|
| `realtime_flow/level` | freshness-weighted; provincial-preferred where fresh+reliable+eligible; **ECCC Datamart/GeoMet floor** (universal, commercial). QC provincial-only. |
| `history` | **ECCC HYDAT / GeoMet primary always** (validated, deepest 1860→) regardless of provincial — provincial realtime is provisional. |
| `water_quality` | **ECCC WQMS primary** (national, keyless, commercial); DataStream + provincial supplement (DataStream on ad-free unless its dataset licence is commercial-OK). Rank by *latest-sample recency + parameter coverage*, not minute-freshness (grab samples). |
| `flood_warning` | **UNION, not pick-one** — surface *all* authoritative warnings for the area (ECCC CAP + BC RFC + QC Vigilance + municipal), deduped. Never suppress a warning because another source is "primary." |
| `flood_forecast` | official feeds now (ECCC water-prediction rasters, provincial RFCs) → our heuristic → model later. No public national point API. |
| `weather` / `aqi` | ad-supported: **MET Norway + ECCC AQHI + ECCC CityPage**; ad-free: Open-Meteo (richer vars) also allowed. |
| `tide` | CHS IWLS (only source). | `smoke` | ECCC FireWork; CWFIS for active fire. |

**Note:** warnings/advisories are a *union* layer; conditions/readings are a *pick-the-best* layer.
The resolver returns a ranked list for the latter and "all eligible" for the former.

## 5. Scoring inputs come from the probe suite (evidence, not guesswork)

The DS-STD-2026.2 suite now records, per source, `data_age_minutes` (freshness) and the
classified `reason_category` history (reliability). A scheduled probe run — or the app's own
fetch telemetry once ingesting — keeps `SOURCE_PROFILE`'s dynamic fields current. Observed
2026-10-19 realtime freshness (illustrative): QC Vigilance ~7 min, ECCC GeoMet/Datamart
~30–42 min, NL ADRS ~4 h, MB FloodInfo ~18 h. So for a QC station the resolver prefers
Vigilance (mandatory + freshest); for an NL/MB station it would prefer ECCC on freshness unless
the provincial feed is the only one carrying that gauge.

## 6. Physical-station deduplication (prerequisite)

The resolver operates on *physical* stations, so sources must be deduped first:
- **Key by WSC `STATION_NUMBER`** where present (provincial feeds usually carry it — NL ADRS has
  `WSC_NUM`; ON KiWIS / MB map to it).
- Else **spatial + name match** (nearest gauge within ~100 m, fuzzy name).
One physical gauge → one resolved reading from the winning source; keep the others as fallbacks.
(This also lets corridor reaches from HydroRIVERS snap to a single deduped gauge.)

## 7. Data structures (sketch)

```python
SOURCE_PROFILE = {
  "SRC-ECCC-DATAMART": dict(authority=0.9, commercial_ok="yes", cadence_min=60,
                            granularity=0.6, data_types={"realtime_flow","realtime_level"},
                            jurisdictions=ALL, federal=True),
  "SRC-QC-VIGILANCE":  dict(authority=0.95, commercial_ok="yes", cadence_min=15,
                            granularity=0.8, data_types={"realtime_flow","realtime_level",
                            "flood_warning"}, jurisdictions={"QC"}, federal=False),
  # … seeded from the DS-STD source→surface matrix …
}
JURISDICTION_POLICY = {
  "QC": {"realtime_flow": {"force": ["SRC-QC-VIGILANCE"]}},
  "AB": {"*": {"ad_free_only": ["SRC-AB-RIVERS"]}},
  "SK": {"*": {"ad_free_only": ["SRC-SK-WSA"]}},
}
# dynamic, refreshed from probe coverage.csv / telemetry:
METRICS[source_id] = dict(data_age_minutes=…, reliability=…)
```

## 8. Phasing (don't build it all at once)

1. **v0** — gate (coverage + surface licence) + provincial-preferred order + ECCC floor + QC/AB/SK overrides + freshness tiebreak. Static profiles; freshness from the latest probe run.
2. **v1** — add measured reliability + circuit breaker; weighted scoring; physical-station dedup.
3. **v2** — live fetch telemetry feeds `METRICS`; per-data-type tuning; municipal advisory/beach layer.

v0 already delivers the user's intent — "provincial/municipal primary, ECCC as a reliable floor,
freshest-wins among equals, licensing decides the page not the ingestion" — with the scoring and
telemetry layered on as evidence accrues.
