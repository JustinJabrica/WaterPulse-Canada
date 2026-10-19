# WaterPulse Data-Source Standard — DS-STD-2026.3: Municipal/Provincial/National Expansion + Methodology & Reliability

**Status:** addendum to DS-STD-2026.1/.2 · **Run date:** 2026-10-19 · **Author:** WaterPulse engineering

> This part (a) expands the probe suite into **municipal, additional-provincial, and additional-
> national** sources, live-testing what can be pulled; and (b) documents **how every condition,
> rating, prediction, and recommendation is computed and how reliable each is** — the evidence base
> for the in-app `/methodology` living-documentation page. References are IEEE-numbered (§6).

## 1. Scope & method

Driven by the directive to *identify, test, and utilize every additional water/weather source
(municipal, provincial, national)* and to *explain the calculation/prediction/recommendation logic
and its reliability*. All probes are read-only and follow the DS-STD patterns (CKAN `package_show`,
Socrata SODA, ArcGIS REST, OGC-API-Features, KiWIS). Each source carries a truthful lifecycle
**status** — **Implemented** (wired + serving), **Research & Testing** (probe-verified), **Possible**
(identified, not yet verified) — mirrored in the frontend `sourceRegistry` that powers the
`/methodology` page and the forthcoming per-station source line.

## 2. New sources tested (2026-10-19)

12 new probes added; **11 retrievable**, 1 correctly key-gated. Suite total: 135 probes.

| source | id | type | verdict | licence / commercial | → status |
|---|---|---|---|---|---|
| ECCC SWOB partner weather stations [1] | SRC-ECCC-SWOB | OGC-API GeoJSON | **OK** (221 obs fields; national density) | OGL-Canada / yes | Testing |
| Aviation METAR, Canadian aerodromes [2] | SRC-AWC-METAR | REST JSON | **OK** (age ~13 min; ~190 CYxx) | US public domain / yes | Testing |
| Grand River CA (KiWIS) [3] | SRC-ON-GRCA | KiWIS JSON | **OK** (reusable across 36 ON CAs) | GRCA Open Data / yes | Testing |
| City of Calgary river levels/flows [4] | SRC-CITY-CALGARY | Socrata | **OK** (5-min level+flow) | OGL-Calgary / yes | Testing |
| City of Edmonton water levels/flows [5] | SRC-CITY-EDMONTON | Socrata | **OK** | OGL-Edmonton / yes | Testing |
| City of Winnipeg river levels (+CSO) [6] | SRC-CITY-WINNIPEG | Socrata | **OK** (CSO feed also available) | OGL-Winnipeg / yes | Testing |
| City of Toronto beach water quality [7] | SRC-CITY-TORONTO-BEACH | CKAN | **OK** (daily E. coli) | OGL-Toronto / yes | Testing |
| Montréal RSMA riverbank water quality [8] | SRC-CITY-MONTREAL-RSMA | CKAN | **OK** (~500 stns) | CC-BY 4.0 / yes | Testing |
| NRCan EGS SAR flood extent [9] | SRC-NRCAN-EGS-FLOOD | ArcGIS REST | **OK** (event-driven) | OGL-Canada / yes | Testing |
| ECCC marine forecasts/warnings [10] | SRC-ECCC-MARINE | OGC-API GeoJSON | **OK** (experimental) | OGL-Canada / yes | Testing |
| Yukon Water Data Explorer [11] | SRC-YT-WATER | CKAN | **OK** (metadata; Shiny/file data) | Yukon open / unknown | Testing |
| 511 Alberta road-weather stations [12] | SRC-AB-511-RWIS | REST JSON | **key-gated** (HTTP 400 w/o key) | 511 AB terms / unknown | **Possible** |

**Honest non-promotion:** SRC-AB-511-RWIS (dev-key required), and the un-probed candidates
SRC-ON-TRCA, SRC-METROVAN-BEACH, SRC-HRM-BEACH, SRC-NS-WATER, SRC-PE-GW, SRC-NB-RIVERWATCH,
SRC-SWIMGUIDE [13], SRC-COCORAHS [14] remain **Possible** until their endpoints/terms are verified.

**Freshness caveat:** Edmonton, Winnipeg, and SWOB report inflated `data_age_minutes` because those
feeds need a source-specific sort/time-column; retrievability (the promotion criterion) is
unaffected and the live-health layer (DS-STD P3) will normalize this.

**Registry after this round:** 77 catalogued sources — **5 Implemented, 63 Research & Testing,
9 Possible**.

**Full sanctioned run** `probes-20261019T121356Z` (130 sanctioned probes): **124/130 retrievable in
361 s, zero regressions.** The 6 non-retrievable are all documented gates — 3 GSC SensorThings
groundwater `dns_error` (pre-existing), 2 DataStream `http_401` (API key), 1 511-Alberta `http_400`
(developer key). `commercial_ok`: yes 121, unknown 4, non-commercial 3, conditional 2. All 5
`municipal` probes retrievable. Net vs DS-STD-2026.2 (113/118): +12 sanctioned probes, +11
retrievable — every new sanctioned probe behaved as designed.

## 3. How conditions, ratings, predictions & recommendations are computed

Documented faithfully from the implementation (`app/services/readings_refresh.py`) and the
authoritative methodology literature:

- **Water level & flow.** Level is measured; **discharge is derived from a station rating curve, not
  measured** — most uncertain at high flow and when ice breaks the stage–discharge relation [15],
  [16]. Real-time values are **provisional** (ECCC QA/QC flag 1=preliminary → 4=approved) and only
  become validated in the HYDAT archive months–years later [15].
- **Ratings (very low → very high).** A reading is placed as a percentile of the same station's
  history within a ±7-day calendar window, pooled across the retained years; buckets `<P10 / <P25 /
  ≤P75 / ≤P90 / >P90`. This adapts the USGS WaterWatch convention (`<10/10–24/25–75/76–90/>90` over
  ≥30 yr) [17] and the WMO normal guidance (30-yr, ≥24 yr) [18]. **WaterPulse currently retains a
  5-year window (development stage); the goal is the full available record** (HYDAT ~1860+), which
  tightens the percentiles toward the convention. Ratings are suppressed below 5 pooled values.
- **Reservoir % full.** Operator-reported (Government of Alberta), not computed by WaterPulse.
- **Weather & AQI.** Open-Meteo values passed through [19]; note the current US-AQI (0–500) vs
  Canada's native **AQHI** (1–10+, a combined O₃/NO₂/PM2.5 health-risk index) [20] — ECCC AQHI is the
  commercial-OK Canadian index for ad-supported surfaces.
- **Predictions.** WaterPulse mirrors official issuers; ECCC NSRPS/DHPS produces ~6-day gridded
  river-discharge forecasts over ~part of Canada via WATROUTE routing [21], and CaPA/HRDPA gives
  best-estimate precip analysis (underestimates heavy/solid precip; sparse north of 60°N) [22]. No
  public point/reach streamflow-forecast API exists; forecasts are labelled as model estimates with
  horizon/issue time.
- **Recommendations.** Recreation suitability (planned) is advisory-only and conservatively gated.
- **Modeled attributes.** HydroRIVERS `DIS_AV_CMS` is modeled long-term climatology (WaterGAP
  downscaled), **not** a current value [23] — labelled as such.

## 4. Reliability tiers (how much to trust each value)

Ordered most → least certain [15]–[24]: **(1) Observed–validated** (HYDAT-approved);
**(2) Observed–provisional** (real-time, revisable; ice-affected winter discharge least certain);
**(3) Official forecast/model** (DHPS, CaPA, AQHI forecasts — best estimate, not a guarantee);
**(4) Derived/modeled** (our percentile ratings; HydroRIVERS climatology); **(5) Crowd-sourced**
(never an automatic safety signal). WaterPulse surfaces the tier + "last updated" rather than hiding
it, and **defers to official flood/emergency issuers** — modelled on published flood-app liability
practice [25], [26].

## 5. Source → surface (commercial vs ad-free)

Per the confirmed ad-supported model, `commercial_ok` governs *where* data appears, not whether it is
ingested: commercial-OK sources (ECCC/WSC, MET Norway, ECCC AQHI, provincial/municipal OGL, CC-BY,
HydroSHEDS, CHS, CWFIS/FireWork, NRCan EGS, SWOB, METAR public-domain) → ad-supported; non-commercial
/ conditional / unknown (Open-Meteo free tier, AB/SK, DataStream per-dataset, 511-AB, Swim Guide,
CoCoRaHS) → ad-free. Every capability retains ≥1 commercial-OK option.

## 6. References (IEEE)

[1] Environment and Climate Change Canada, "Surface Weather/Observation (SWOB) partner network," Meteorological Service of Canada, 2026. [Online]. Available: https://api.weather.gc.ca/collections/swob-realtime. [Accessed: Oct. 19, 2026].
[2] Aviation Weather Center, "METAR/TAF data API," US National Weather Service, 2026. [Online]. Available: https://aviationweather.gov/data/api/. [Accessed: Oct. 19, 2026].
[3] Grand River Conservation Authority, "Water data web services (KiWIS)," 2026. [Online]. Available: https://data.grandriver.ca/webservices-monitoring.html. [Accessed: Oct. 19, 2026].
[4] City of Calgary, "River Levels and Flows (Open Data)," 2026. [Online]. Available: https://data.calgary.ca/Environment/River-Levels-and-Flows/5fdg-ifgr. [Accessed: Oct. 19, 2026].
[5] City of Edmonton, "Water Levels and Flows (Open Data)," 2026. [Online]. Available: https://data.edmonton.ca/. [Accessed: Oct. 19, 2026].
[6] City of Winnipeg, "River Water Levels and CSO monitoring (Open Data)," 2026. [Online]. Available: https://data.winnipeg.ca/. [Accessed: Oct. 19, 2026].
[7] City of Toronto, "Toronto Beaches Water Quality (Open Data)," 2026. [Online]. Available: https://open.toronto.ca/dataset/toronto-beaches-water-quality/. [Accessed: Oct. 19, 2026].
[8] Ville de Montréal, "RSMA — qualité de l'eau en rive (QUALO)," 2026. [Online]. Available: https://donnees.montreal.ca/dataset/rsma-qualite-de-l-eau-en-rive-qualo. [Accessed: Oct. 19, 2026].
[9] Natural Resources Canada, "Emergency Geomatics Service flood product (RCM/Sentinel-1 SAR)," 2026. [Online]. Available: https://geo.ca/flood-mapping/. [Accessed: Oct. 19, 2026].
[10] Environment and Climate Change Canada, "Marine weather forecasts (experimental)," 2026. [Online]. Available: https://api.weather.gc.ca/collections/marineweather-realtime. [Accessed: Oct. 19, 2026].
[11] Government of Yukon, "Water Data Explorer," 2026. [Online]. Available: https://open.yukon.ca/data/water-data-explorer. [Accessed: Oct. 19, 2026].
[12] Government of Alberta, "511 Alberta weather-station API," 2026. [Online]. Available: https://511.alberta.ca/developers/doc. [Accessed: Oct. 19, 2026].
[13] Swim Drink Fish, "Swim Guide," 2026. [Online]. Available: https://www.theswimguide.org/. [Accessed: Oct. 19, 2026].
[14] CoCoRaHS, "Community Collaborative Rain, Hail and Snow Network — Canada," 2026. [Online]. Available: https://www.cocorahs.org/canada.aspx. [Accessed: Oct. 19, 2026].
[15] Water Survey of Canada, "Water level and flow — FAQ (provisional vs approved; grades/symbols)," Environment and Climate Change Canada, 2026. [Online]. Available: https://wateroffice.ec.gc.ca/contactus/faq_e.html. [Accessed: Oct. 19, 2026].
[16] Environment and Climate Change Canada, "MSC Datamart hydrometric data README," 2026. [Online]. Available: https://eccc-msc.github.io/open-data/msc-data/obs_hydrometric/readme_hydrometric-datamart_en/. [Accessed: Oct. 19, 2026].
[17] U.S. Geological Survey, "WaterWatch — explanation of streamflow percentile classes," Fact Sheet FS 052-02, 2002. [Online]. Available: https://pubs.usgs.gov/fs/fs-052-02/pdf/fs05202web.pdf. [Accessed: Oct. 19, 2026].
[18] World Meteorological Organization, "WMO Guidelines on the Calculation of Climate Normals," WMO-No. 1203, 2017.
[19] Open-Meteo, "Weather Forecast API," 2026. [Online]. Available: https://open-meteo.com/en/docs. [Accessed: Oct. 19, 2026].
[20] Environment and Climate Change Canada, "About the Air Quality Health Index," 2026. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/air-quality-health-index.html. [Accessed: Oct. 19, 2026].
[21] V. Fortin et al., "A hydrological prediction system based on the SVS land-surface scheme and WATROUTE (NSRPS/DHPS)," NOAA GLERL, 2016. [Online]. Available: https://www.glerl.noaa.gov/pubs/fulltext/2016/20160051.pdf. [Accessed: Oct. 19, 2026].
[22] M. Fortin et al., "Ten years of science based on the Canadian Precipitation Analysis (CaPA)," Atmosphere-Ocean, 2018. [Online]. Available: https://doi.org/10.1080/07055900.2018.1474728. [Accessed: Oct. 19, 2026].
[23] B. Lehner and G. Grill, "Global river hydrography and network routing (HydroRIVERS/DIS_AV_CMS)," Hydrological Processes, vol. 27, no. 15, pp. 2171–2186, 2013.
[24] The Gordon Foundation, "DataStream data governance & QC policy," 2026. [Online]. Available: https://datastream.org/en-ca/documentation/data-policy. [Accessed: Oct. 19, 2026].
[25] King County Flood Control District, "Flood Warning App — liability disclaimer," 2026. [Online]. Available: https://kingcountyfloodcontrol.org/be-flood-ready/flood-warning-app/. [Accessed: Oct. 19, 2026].
[26] Floodi, "Terms of Service — safety/crowdsource disclaimers," 2026. [Online]. Available: https://floodi.app/terms/. [Accessed: Oct. 19, 2026].

## 7. How to reproduce
```bash
docker compose run --rm -T --no-deps --entrypoint python backend -m tests.probe_sources --category municipal
#   …also: weather | flood | current   (new ids: SRC-ECCC-SWOB, SRC-AWC-METAR, SRC-ON-GRCA, SRC-CITY-*, …)
# key-gated: WP_511AB_API_KEY unblocks SRC-AB-511-RWIS
```
