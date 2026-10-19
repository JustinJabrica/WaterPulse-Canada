/**
 * sourceRegistry — the single source of truth for every data source WaterPulse
 * uses, is testing, or is considering. It drives the /methodology living-doc
 * page (geographic source table + IEEE references) and will drive the
 * per-station "source line" (keyed by a reading's resolved `data_source`).
 *
 * Each entry:
 *   id         — canonical source id (matches the DS-STD probe SRC-* ids where applicable)
 *   name       — human-facing short name
 *   operator   — who runs/publishes it
 *   categories — capability tags (level/flow, weather, water-quality, flood, …)
 *   geo        — { level: 'national'|'provincial'|'municipal', province?, city? }
 *   commercial — 'yes' | 'conditional' | 'non-commercial' | 'unknown'  (→ ad surface)
 *   licence    — short licence label
 *   status     — 'implemented' | 'testing' | 'possible'  (MUST be truthful)
 *   url        — canonical reference URL
 *   citation   — IEEE reference body (the page prefixes [n] + a stable number)
 *   depth      — optional: available historical depth note
 *   note       — optional caveat
 *
 * STATUS truthfulness (DS-STD-2026.3): 'implemented' = wired into the app and
 * serving data now; 'testing' = probe-verified fetchable (DS-STD coverage.csv)
 * but not yet wired; 'possible' = identified candidate, not yet probed.
 *
 * Retention note: WaterPulse currently collects a 5-year window (development
 * stage); the goal is the full available record (see each entry's `depth`).
 */

const ACCESSED = "Oct. 19, 2026";

export const SOURCES = [
  // ───────────────────────── IMPLEMENTED (wired + serving data now) ─────────────────────────
  {
    id: "SRC-ECCC-DATAMART", name: "ECCC Datamart (real-time hydrometric)",
    operator: "Environment and Climate Change Canada — Water Survey of Canada",
    categories: ["level", "flow"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada / MSC End-use v2.1.1", status: "implemented",
    url: "https://dd.weather.gc.ca/today/hydrometric/csv/",
    citation: 'Environment and Climate Change Canada, "MSC Datamart — Hydrometric data," Meteorological Service of Canada, 2026. [Online]. Available: https://dd.weather.gc.ca/today/hydrometric/csv/. [Accessed: ' + ACCESSED + "].",
    depth: "real-time ~2 days (hourly) / ~30 days (daily); deep record via HYDAT",
    note: "Discharge is derived from a stage–discharge rating curve, not measured directly; provisional (QA/QC 1–3) until approved.",
  },
  {
    id: "SRC-ECCC-GEOMET", name: "ECCC GeoMet OGC API (hydrometric)",
    operator: "Environment and Climate Change Canada",
    categories: ["level", "flow", "stations", "history"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada / MSC End-use v2.1.1", status: "implemented",
    url: "https://api.weather.gc.ca/",
    citation: 'Environment and Climate Change Canada, "GeoMet-OGC-API: hydrometric collections," Meteorological Service of Canada, 2026. [Online]. Available: https://api.weather.gc.ca/. [Accessed: ' + ACCESSED + "].",
    depth: "daily/monthly/annual back to station start (often decades)",
  },
  {
    id: "SRC-AB-RIVERS", name: "Alberta River Basins",
    operator: "Government of Alberta — Environment and Protected Areas",
    categories: ["level", "flow", "reservoir-capacity"], geo: { level: "provincial", province: "AB" },
    commercial: "non-commercial", licence: "Government of Alberta copyright", status: "implemented",
    url: "https://rivers.alberta.ca/",
    citation: 'Government of Alberta, "Alberta River Basins," Environment and Protected Areas, 2026. [Online]. Available: https://rivers.alberta.ca/. [Accessed: ' + ACCESSED + "].",
    note: "Non-commercial reuse only (ad-free surfaces). Reservoir % full is Alberta-reported, not computed by WaterPulse.",
  },
  {
    id: "SRC-OPEN-METEO", name: "Open-Meteo (weather forecast)",
    operator: "Open-Meteo", categories: ["weather"], geo: { level: "national" },
    commercial: "non-commercial", licence: "CC-BY 4.0 (free tier non-commercial)", status: "implemented",
    url: "https://open-meteo.com/",
    citation: 'Open-Meteo, "Weather Forecast API," 2026. [Online]. Available: https://open-meteo.com/en/docs. [Accessed: ' + ACCESSED + "].",
    note: "Free tier is non-commercial (ad-free surfaces); a paid commercial tier exists. Values passed through and interpreted client-side.",
  },
  {
    id: "SRC-OPEN-METEO-AQI", name: "Open-Meteo Air Quality (US AQI/PM)",
    operator: "Open-Meteo", categories: ["aqi"], geo: { level: "national" },
    commercial: "non-commercial", licence: "CC-BY 4.0 (free tier non-commercial)", status: "implemented",
    url: "https://open-meteo.com/en/docs/air-quality-api",
    citation: 'Open-Meteo, "Air Quality API," 2026. [Online]. Available: https://open-meteo.com/en/docs/air-quality-api. [Accessed: ' + ACCESSED + "].",
    note: "Provides US AQI (0–500); Canada's native scale is AQHI (1–10+). See ECCC AQHI for the commercial-OK Canadian index.",
  },

  // ───────────────────────── RESEARCH & TESTING (probe-verified, not yet wired) ─────────────────────────
  // National / federal (ECCC / WSC / NRCan / DFO / HydroSHEDS)
  {
    id: "SRC-HYDAT", name: "HYDAT (validated historical archive)",
    operator: "Water Survey of Canada", categories: ["history"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/monitoring/survey/data-products-services/national-archive-hydat.html",
    citation: 'Water Survey of Canada, "National Water Data Archive: HYDAT," Environment and Climate Change Canada, 2026. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/monitoring/survey/data-products-services/national-archive-hydat.html. [Accessed: ' + ACCESSED + "].",
    depth: "validated daily means to ~1860; the deep record for percentiles/trends",
  },
  {
    id: "SRC-ECCC-GEOMET-DAILY", name: "ECCC GeoMet daily/monthly means", operator: "Environment and Climate Change Canada",
    categories: ["history"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://api.weather.gc.ca/collections/hydrometric-daily-mean", citation: 'Environment and Climate Change Canada, "GeoMet hydrometric daily/monthly mean collections," 2026. [Online]. Available: https://api.weather.gc.ca/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-ECCC-CITYPAGE", name: "ECCC City Page Weather", operator: "Environment and Climate Change Canada",
    categories: ["weather"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://dd.weather.gc.ca/citypage_weather/", citation: 'Environment and Climate Change Canada, "City Page Weather XML," Meteorological Service of Canada, 2026. [Online]. Available: https://dd.weather.gc.ca/citypage_weather/. [Accessed: ' + ACCESSED + "].",
    note: "Commercial-OK weather stack for ad-supported surfaces (with MET Norway).",
  },
  {
    id: "SRC-ECCC-AQHI", name: "ECCC Air Quality Health Index (AQHI)", operator: "Environment and Climate Change Canada",
    categories: ["aqi"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://api.weather.gc.ca/collections/aqhi-observations-realtime", citation: 'Environment and Climate Change Canada, "Air Quality Health Index (AQHI)," 2026. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/air-quality-health-index.html. [Accessed: ' + ACCESSED + "].",
    note: "Canada's native 1–10+ health-risk index (O₃, NO₂, PM2.5). Commercial-OK alternative to Open-Meteo US AQI.",
  },
  {
    id: "SRC-ECCC-CLIMATE", name: "ECCC climate observations (precip/snow)", operator: "Environment and Climate Change Canada",
    categories: ["precip", "stations"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://api.weather.gc.ca/collections/climate-daily", citation: 'Environment and Climate Change Canada, "GeoMet climate observation collections," 2026. [Online]. Available: https://api.weather.gc.ca/. [Accessed: ' + ACCESSED + "].", depth: "station records to the early 1900s",
  },
  {
    id: "SRC-ECCC-WATERPRED", name: "ECCC water-prediction models (WCPS/OHPS/DHPS)", operator: "Environment and Climate Change Canada",
    categories: ["flood", "streamflow-forecast"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://geo.weather.gc.ca/geomet", citation: 'Environment and Climate Change Canada, "GeoMet WMS water-prediction layers (NSRPS/DHPS, WCPS, OHPS)," 2026. [Online]. Available: https://geo.weather.gc.ca/geomet. [Accessed: ' + ACCESSED + "].",
    note: "Deterministic model forecasts (raster, ~6-day, ~50% of Canada). Best estimate, not a bounded prediction; no public point/reach API.",
  },
  {
    id: "SRC-ECCC-CAP", name: "ECCC public weather alerts (CAP)", operator: "Environment and Climate Change Canada",
    categories: ["flood", "alerts"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://dd.weather.gc.ca/today/alerts/cap/", citation: 'Environment and Climate Change Canada, "Public weather alerts (CAP)," Meteorological Service of Canada, 2026. [Online]. Available: https://dd.weather.gc.ca/today/alerts/cap/. [Accessed: ' + ACCESSED + "].",
    note: "National rainfall/flood/thunderstorm warnings. WaterPulse mirrors official alerts, never replaces them.",
  },
  {
    id: "SRC-ECCC-RADAR", name: "ECCC weather radar", operator: "Environment and Climate Change Canada",
    categories: ["precip", "radar"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://geo.weather.gc.ca/geomet", citation: 'Environment and Climate Change Canada, "GeoMet weather radar (RADAR_1KM)," 2026. [Online]. Available: https://geo.weather.gc.ca/geomet. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-ECCC-HRDPA", name: "ECCC precip analysis (HRDPA/CaPA)", operator: "Environment and Climate Change Canada",
    categories: ["precip"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://geo.weather.gc.ca/geomet", citation: 'Environment and Climate Change Canada, "High-Resolution Deterministic Precipitation Analysis (HRDPA/CaPA)," 2026. [Online]. Available: https://eccc-msc.github.io/open-data/msc-data/nwp_hrdpa/. [Accessed: ' + ACCESSED + "].",
    note: "Underestimates heavy/solid precip; sparse-network bias north of 60°N.",
  },
  {
    id: "SRC-ECCC-LIGHTNING", name: "ECCC lightning density", operator: "Environment and Climate Change Canada",
    categories: ["precip", "storm"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://geo.weather.gc.ca/geomet", citation: 'Environment and Climate Change Canada, "GeoMet lightning density," 2026. [Online]. Available: https://geo.weather.gc.ca/geomet. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-ECCC-FIREWORK", name: "ECCC FireWork wildfire-smoke forecast", operator: "Environment and Climate Change Canada",
    categories: ["smoke", "aqi"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://eccc-msc.github.io/open-data/msc-data/nwp_raqdps-fw/", citation: 'Environment and Climate Change Canada, "FireWork (RAQDPS-FW) near-surface smoke forecast," 2026. [Online]. Available: https://eccc-msc.github.io/open-data/msc-data/nwp_raqdps-fw/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-ECCC-OGC-HYDRO", name: "ECCC GeoMet realtime gauges (corridor snap)", operator: "Environment and Climate Change Canada",
    categories: ["level", "flow"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada / MSC End-use", status: "testing",
    url: "https://api.weather.gc.ca/collections/hydrometric-realtime", citation: 'Environment and Climate Change Canada, "GeoMet hydrometric-realtime OGC API," 2026. [Online]. Available: https://api.weather.gc.ca/collections/hydrometric-realtime. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-CHS-IWLS", name: "DFO/CHS water levels & tides (IWLS)", operator: "Fisheries and Oceans Canada — Canadian Hydrographic Service",
    categories: ["tides", "level"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://api-iwls.dfo-mpo.gc.ca/", citation: 'Fisheries and Oceans Canada, "Integrated Water Level System (IWLS) API," Canadian Hydrographic Service, 2026. [Online]. Available: https://api-iwls.dfo-mpo.gc.ca/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-CWFIS-FIRE", name: "CWFIS active-fire hotspots", operator: "Natural Resources Canada — Canadian Forest Service",
    categories: ["wildfire"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://cwfis.cfs.nrcan.gc.ca/", citation: 'Natural Resources Canada, "Canadian Wildland Fire Information System (CWFIS)," Canadian Forest Service, 2026. [Online]. Available: https://cwfis.cfs.nrcan.gc.ca/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-NRCAN-FLOOD", name: "NRCan flood-mapping hub (FHIMP)", operator: "Natural Resources Canada",
    categories: ["flood"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://geo.ca/flood-mapping/", citation: 'Natural Resources Canada, "Flood Hazard Identification and Mapping Program," 2026. [Online]. Available: https://geo.ca/flood-mapping/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-GIN", name: "Groundwater Information Network (GIN)", operator: "Natural Resources Canada — Geological Survey of Canada",
    categories: ["groundwater"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://gin.gw-info.net/", citation: 'Geological Survey of Canada, "Groundwater Information Network (GIN)," Natural Resources Canada, 2026. [Online]. Available: https://gin.gw-info.net/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-STA-GW", name: "Groundwater SensorThings API", operator: "Geological Survey of Canada",
    categories: ["groundwater"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://sensorthings.gw-info.net/", citation: 'Geological Survey of Canada, "Groundwater SensorThings API," Natural Resources Canada, 2026. [Online]. Available: https://sensorthings.gw-info.net/. [Accessed: ' + ACCESSED + "].",
    note: "Intermittent DNS availability observed in DS-STD probing.",
  },
  {
    id: "SRC-CRID", name: "Canadian River Ice Database (CRID)", operator: "Environment and Climate Change Canada",
    categories: ["ice"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://open.canada.ca/", citation: 'Environment and Climate Change Canada, "Canadian River Ice Database (CRID)," 2026. [Online]. Available: https://open.canada.ca/. [Accessed: ' + ACCESSED + "].", depth: "river-ice observations from 1894",
  },
  {
    id: "SRC-LAKEICE", name: "Canadian Lake Ice Database", operator: "Environment and Climate Change Canada",
    categories: ["ice"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://open.canada.ca/", citation: 'Environment and Climate Change Canada, "Canadian Lake Ice Database," 2026. [Online]. Available: https://open.canada.ca/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-CIS-ICE", name: "Canadian Ice Service", operator: "Environment and Climate Change Canada — Canadian Ice Service",
    categories: ["ice"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://iceweb1.cis.ec.gc.ca/", citation: 'Canadian Ice Service, "Ice conditions and products," Environment and Climate Change Canada, 2026. [Online]. Available: https://www.canada.ca/en/environment-climate-change/services/ice-forecasts-observations.html. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-CANSWE", name: "CanSWE snow water equivalent", operator: "Environment and Climate Change Canada (Vionnet et al.)",
    categories: ["snow"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://doi.org/10.5281/zenodo.10835278", citation: 'V. Vionnet et al., "CanSWE: Canadian historical Snow Water Equivalent dataset," Zenodo, 2026. [Online]. Available: https://doi.org/10.5281/zenodo.10835278. [Accessed: ' + ACCESSED + "].", depth: "snow water equivalent from 1928",
  },
  {
    id: "SRC-CIOOS", name: "CIOOS coastal observations (water temp)", operator: "Canadian Integrated Ocean Observing System",
    categories: ["watertemp"], geo: { level: "national" }, commercial: "yes", licence: "CC-BY / OGL / CC0 (per dataset)", status: "testing",
    url: "https://cioos.ca/", citation: 'Canadian Integrated Ocean Observing System, "CIOOS ERDDAP data servers," 2026. [Online]. Available: https://cioos.ca/. [Accessed: ' + ACCESSED + "].", note: "Coastal/estuarine, not inland rivers.",
  },
  {
    id: "SRC-RIVTEMP", name: "RivTemp river temperature (via DataStream)", operator: "RivTemp network / The Gordon Foundation",
    categories: ["watertemp"], geo: { level: "national" }, commercial: "conditional", licence: "DataStream per-dataset", status: "testing",
    url: "https://datastream.org/", citation: 'The Gordon Foundation, "RivTemp river-temperature data on DataStream," 2026. [Online]. Available: https://datastream.org/. [Accessed: ' + ACCESSED + "].", note: "Requires a free DataStream API key (x-api-key).",
  },
  {
    id: "SRC-DATASTREAM-WQ", name: "DataStream water quality", operator: "The Gordon Foundation",
    categories: ["water-quality"], geo: { level: "national" }, commercial: "conditional", licence: "per-dataset (ODC-By / PDDL / OGL)", status: "testing",
    url: "https://datastream.org/", citation: 'The Gordon Foundation, "DataStream open water-quality platform (OData v4 API)," 2026. [Online]. Available: https://datastream.org/en-ca/documentation/api. [Accessed: ' + ACCESSED + "].",
    note: "Requires a free API key. QC varies per contributing dataset; judge reliability per dataset.",
  },
  {
    id: "SRC-ECCC-WQMS", name: "ECCC National Long-term Water Quality Monitoring", operator: "Environment and Climate Change Canada",
    categories: ["water-quality"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "testing",
    url: "https://open.canada.ca/data/en/dataset/67b44816-9764-4609-ace1-68dc1764e9ea", citation: 'Environment and Climate Change Canada, "National Long-term Water Quality Monitoring Data," 2026. [Online]. Available: https://open.canada.ca/data/en/dataset/67b44816-9764-4609-ace1-68dc1764e9ea. [Accessed: ' + ACCESSED + "].", depth: "2000–present; grab samples, not live sondes",
  },
  {
    id: "SRC-MET-NORWAY", name: "MET Norway Locationforecast", operator: "Norwegian Meteorological Institute",
    categories: ["weather"], geo: { level: "national" }, commercial: "yes", licence: "CC-BY 4.0 / NLOD 2.0", status: "testing",
    url: "https://api.met.no/", citation: 'Norwegian Meteorological Institute, "Locationforecast API," 2026. [Online]. Available: https://api.met.no/weatherapi/locationforecast/2.0/documentation. [Accessed: ' + ACCESSED + "].", note: "Commercial-OK weather for ad-supported surfaces.",
  },
  // National hydrography / topology (drainage)
  {
    id: "SRC-HYDRORIVERS", name: "HydroSHEDS HydroRIVERS", operator: "World Wildlife Fund / HydroSHEDS (Lehner & Grill)",
    categories: ["river-network"], geo: { level: "national" }, commercial: "yes", licence: "HydroSHEDS (attribution)", status: "testing",
    url: "https://www.hydrosheds.org/products/hydrorivers", citation: 'B. Lehner and G. Grill, "Global river hydrography and network routing (HydroRIVERS)," Hydrological Processes, vol. 27, no. 15, pp. 2171–2186, 2013. [Online]. Available: https://www.hydrosheds.org/products/hydrorivers. [Accessed: ' + ACCESSED + "].",
    note: "River network + flow direction (NEXT_DOWN). DIS_AV_CMS is modeled long-term climatology, not current discharge.",
  },
  {
    id: "SRC-HYDROSHEDS", name: "HydroSHEDS HydroBASINS", operator: "World Wildlife Fund / HydroSHEDS",
    categories: ["watershed"], geo: { level: "national" }, commercial: "yes", licence: "HydroSHEDS (attribution)", status: "testing",
    url: "https://www.hydrosheds.org/products/hydrobasins", citation: 'B. Lehner and G. Grill, "HydroBASINS nested watershed polygons," HydroSHEDS, 2013. [Online]. Available: https://www.hydrosheds.org/products/hydrobasins. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-BASINMAKER", name: "BasinMaker N. American routing product", operator: "University of Waterloo hydrology group",
    categories: ["river-network"], geo: { level: "national" }, commercial: "yes", licence: "MIT", status: "testing",
    url: "https://doi.org/10.5281/zenodo.4728185", citation: 'M. Han et al., "North American Lake-River Routing Product v2.1 (BasinMaker)," Zenodo, 2021. [Online]. Available: https://doi.org/10.5281/zenodo.4728185. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-NHN", name: "National Hydro Network (NHN)", operator: "Natural Resources Canada", categories: ["watershed"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada 2.0", status: "testing", url: "https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977",
    citation: 'Natural Resources Canada, "National Hydro Network (NHN)," 2026. [Online]. Available: https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-NHN-NLFLOW", name: "NHN directed flow network (NLFLOW)", operator: "Natural Resources Canada", categories: ["river-network"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada", status: "testing", url: "http://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_nhn_rhn/",
    citation: 'Natural Resources Canada, "National Hydro Network — network linear flow (NLFLOW)," 2026. [Online]. Available: http://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_nhn_rhn/. [Accessed: ' + ACCESSED + "].",
  },
  {
    id: "SRC-WSC-BASINS", name: "WSC gauge drainage basins", operator: "Water Survey of Canada", categories: ["watershed"], geo: { level: "national" },
    commercial: "yes", licence: "OGL-Canada 2.0", status: "testing", url: "https://open.canada.ca/data/en/dataset/0c121878-ac23-46f5-95df-eb9960753375",
    citation: 'Water Survey of Canada, "WSC drainage basin polygons," Environment and Climate Change Canada, 2026. [Online]. Available: https://open.canada.ca/data/en/dataset/0c121878-ac23-46f5-95df-eb9960753375. [Accessed: ' + ACCESSED + "].",
  },

  // Provincial (Research & Testing)
  { id: "SRC-BC-RFC", name: "BC River Forecast Centre (flood warnings)", operator: "Province of British Columbia", categories: ["flood"], geo: { level: "provincial", province: "BC" }, commercial: "yes", licence: "OGL-BC", status: "testing", url: "https://bcrfc.env.gov.bc.ca/warnings/", citation: 'Province of British Columbia, "River Forecast Centre flood warnings/advisories," 2026. [Online]. Available: https://bcrfc.env.gov.bc.ca/warnings/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-BC-AQUARIUS", name: "BC AQUARIUS water data", operator: "Province of British Columbia", categories: ["level", "flow"], geo: { level: "provincial", province: "BC" }, commercial: "yes", licence: "OGL-BC", status: "testing", url: "https://bcmoe-prod.aquaticinformatics.net/", citation: 'Province of British Columbia, "ENV AQUARIUS WebPortal," 2026. [Online]. Available: https://bcmoe-prod.aquaticinformatics.net/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-BC-ASWS", name: "BC Automated Snow Weather Stations", operator: "Province of British Columbia", categories: ["snow", "weather", "precip"], geo: { level: "provincial", province: "BC" }, commercial: "yes", licence: "OGL-BC", status: "testing", url: "https://www.env.gov.bc.ca/wsd/data_searches/snow/", citation: 'Province of British Columbia, "Automated Snow Weather Station data," 2026. [Online]. Available: https://www.env.gov.bc.ca/wsd/data_searches/snow/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-BC-FWA", name: "BC Freshwater Atlas", operator: "Province of British Columbia", categories: ["watershed"], geo: { level: "provincial", province: "BC" }, commercial: "yes", licence: "OGL-BC 2.0", status: "testing", url: "https://catalogue.data.gov.bc.ca/dataset/freshwater-atlas", citation: 'Province of British Columbia, "Freshwater Atlas," 2026. [Online]. Available: https://catalogue.data.gov.bc.ca/dataset/freshwater-atlas. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-BC-ENMODS", name: "BC EnMoDS water quality", operator: "Province of British Columbia", categories: ["water-quality"], geo: { level: "provincial", province: "BC" }, commercial: "yes", licence: "OGL-BC", status: "testing", url: "https://open.canada.ca/data/en/dataset/83a585fe-effb-48bd-8a03-d35db4eeb1bb", citation: 'Province of British Columbia, "EnMoDS environmental monitoring results," 2026. [Online]. Available: https://open.canada.ca/data/en/dataset/83a585fe-effb-48bd-8a03-d35db4eeb1bb. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-AB-RWQI", name: "Alberta River Water Quality Index", operator: "Government of Alberta", categories: ["water-quality"], geo: { level: "provincial", province: "AB" }, commercial: "yes", licence: "OGL-Alberta", status: "testing", url: "https://open.alberta.ca/opendata/river-water-quality-index-alberta", citation: 'Government of Alberta, "River Water Quality Index," 2026. [Online]. Available: https://open.alberta.ca/opendata/river-water-quality-index-alberta. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-AB-SNOW", name: "Alberta snow pillows", operator: "Government of Alberta", categories: ["snow"], geo: { level: "provincial", province: "AB" }, commercial: "unknown", licence: "OGL-Alberta (unconfirmed)", status: "testing", url: "https://rivers.alberta.ca/", citation: 'Government of Alberta, "Snow pillow / snow course data," 2026. [Online]. Available: https://rivers.alberta.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-SK-WSA", name: "Saskatchewan Water Security Agency", operator: "Saskatchewan Water Security Agency", categories: ["level", "flow"], geo: { level: "provincial", province: "SK" }, commercial: "no", licence: "SK Crown copyright", status: "testing", url: "https://www.wsask.ca/", citation: 'Saskatchewan Water Security Agency, "Hydrographs," 2026. [Online]. Available: https://www.wsask.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-MB-FLOODINFO", name: "Manitoba FloodInfo / Forecast Centre", operator: "Province of Manitoba", categories: ["level", "flow", "flood"], geo: { level: "provincial", province: "MB" }, commercial: "yes", licence: "OpenMB", status: "testing", url: "https://www.manitoba.ca/flooding/", citation: 'Province of Manitoba, "Flood Information / Hydrologic Forecast Centre," 2026. [Online]. Available: https://www.manitoba.ca/flooding/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-MB-HFC", name: "Manitoba Hydrologic Forecast Centre (bulletins)", operator: "Province of Manitoba", categories: ["flood"], geo: { level: "provincial", province: "MB" }, commercial: "unknown", licence: "unspecified", status: "testing", url: "https://www.gov.mb.ca/mit/floodinfo/forecast_centre/", citation: 'Province of Manitoba, "Hydrologic Forecast Centre bulletins," 2026. [Online]. Available: https://www.gov.mb.ca/mit/floodinfo/forecast_centre/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-KIWIS", name: "Ontario Surface Water Monitoring (KiWIS)", operator: "Ontario Ministry of Natural Resources", categories: ["level", "flow", "stations"], geo: { level: "provincial", province: "ON" }, commercial: "yes", licence: "OGL-Ontario", status: "testing", url: "https://www.ontario.ca/page/surface-water-monitoring", citation: 'Ontario Ministry of Natural Resources, "Surface Water Monitoring Centre (KiWIS)," 2026. [Online]. Available: https://www.ontario.ca/page/surface-water-monitoring. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-CO", name: "Conservation Ontario flood messages", operator: "Conservation Ontario", categories: ["flood"], geo: { level: "provincial", province: "ON" }, commercial: "unknown", licence: "unspecified", status: "testing", url: "https://conservationontario.ca/", citation: 'Conservation Ontario, "Flood forecasting and warning messages," 2026. [Online]. Available: https://conservationontario.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-OIH", name: "Ontario Integrated Hydrology", operator: "Government of Ontario", categories: ["watershed", "river-network"], geo: { level: "provincial", province: "ON" }, commercial: "yes", licence: "OGL-Ontario 1.0", status: "testing", url: "https://geohub.lio.gov.on.ca/", citation: 'Government of Ontario, "Ontario Integrated Hydrology data," 2026. [Online]. Available: https://geohub.lio.gov.on.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-PWQMN", name: "Ontario Provincial (Stream) Water Quality", operator: "Government of Ontario", categories: ["water-quality"], geo: { level: "provincial", province: "ON" }, commercial: "yes", licence: "OGL-Ontario", status: "testing", url: "https://data.ontario.ca/dataset/provincial-stream-water-quality-monitoring-network", citation: 'Government of Ontario, "Provincial (Stream) Water Quality Monitoring Network," 2026. [Online]. Available: https://data.ontario.ca/dataset/provincial-stream-water-quality-monitoring-network. [Accessed: ' + ACCESSED + "].", depth: "1964–present" },
  { id: "SRC-ON-PGMN", name: "Ontario Provincial Groundwater Monitoring", operator: "Government of Ontario", categories: ["groundwater"], geo: { level: "provincial", province: "ON" }, commercial: "yes", licence: "OGL-Ontario", status: "testing", url: "https://data.ontario.ca/", citation: 'Government of Ontario, "Provincial Groundwater Monitoring Network," 2026. [Online]. Available: https://data.ontario.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-QC-VIGILANCE", name: "Québec Vigilance (hydrometric + flood)", operator: "Gouvernement du Québec (MELCCFP)", categories: ["level", "flow", "flood"], geo: { level: "provincial", province: "QC" }, commercial: "yes", licence: "CC-BY 4.0", status: "testing", url: "https://vigilance.gouv.qc.ca/", citation: 'Gouvernement du Québec, "Vigilance — surveillance hydrométrique et crues," MELCCFP, 2026. [Online]. Available: https://vigilance.gouv.qc.ca/. [Accessed: ' + ACCESSED + "].", note: "Québec's mandatory provincial real-time source (ECCC carries ~15 QC stations)." },
  { id: "SRC-QC-IQBP", name: "Québec Réseau-rivières (IQBP) water quality", operator: "Gouvernement du Québec", categories: ["water-quality"], geo: { level: "provincial", province: "QC" }, commercial: "yes", licence: "CC-BY 4.0", status: "testing", url: "https://www.donneesquebec.ca/recherche/fr/dataset/suivi-physicochimique-des-rivieres-et-du-fleuve", citation: 'Gouvernement du Québec, "Suivi physicochimique des rivières (IQBP)," 2026. [Online]. Available: https://www.donneesquebec.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-QC-GRHQ", name: "Québec hydrographic network (GRHQ)", operator: "Gouvernement du Québec", categories: ["watershed"], geo: { level: "provincial", province: "QC" }, commercial: "yes", licence: "CC-BY 4.0", status: "testing", url: "https://www.donneesquebec.ca/", citation: 'Gouvernement du Québec, "Géographie du réseau hydrographique (GRHQ)," 2026. [Online]. Available: https://www.donneesquebec.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-QC-RSESQ", name: "Québec groundwater network (RSESQ)", operator: "Gouvernement du Québec", categories: ["groundwater"], geo: { level: "provincial", province: "QC" }, commercial: "yes", licence: "CC-BY 4.0", status: "testing", url: "https://www.donneesquebec.ca/", citation: 'Gouvernement du Québec, "Réseau de suivi des eaux souterraines (RSESQ)," 2026. [Online]. Available: https://www.donneesquebec.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-NL-ADRS", name: "Newfoundland & Labrador ADRS", operator: "Government of Newfoundland and Labrador", categories: ["level", "flow", "watertemp"], geo: { level: "provincial", province: "NL" }, commercial: "yes", licence: "OGL-NL", status: "testing", url: "https://www.gov.nl.ca/ecc/waterres/realtime/", citation: 'Government of Newfoundland and Labrador, "Real-Time Hydrometric Data (ADRS)," 2026. [Online]. Available: https://www.gov.nl.ca/ecc/waterres/realtime/. [Accessed: ' + ACCESSED + "]." },

  // ───────────────────────── POSSIBLE (identified, not yet probed — Phase 2 targets) ─────────────────────────
  { id: "SRC-ECCC-SWOB", name: "ECCC SWOB partner weather stations", operator: "Environment and Climate Change Canada", categories: ["weather"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "possible", url: "https://api.weather.gc.ca/collections/swob-realtime", citation: 'Environment and Climate Change Canada, "Surface Weather/Observation (SWOB) partner network," 2026. [Online]. Available: https://api.weather.gc.ca/collections/swob-realtime. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-AWC-METAR", name: "Aviation METAR/TAF (Canadian airports)", operator: "US NWS Aviation Weather Center", categories: ["weather"], geo: { level: "national" }, commercial: "yes", licence: "US Gov public domain", status: "possible", url: "https://aviationweather.gov/data/api/", citation: 'Aviation Weather Center, "METAR/TAF data API," US National Weather Service, 2026. [Online]. Available: https://aviationweather.gov/data/api/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ECCC-MARINE", name: "ECCC marine forecasts & warnings", operator: "Environment and Climate Change Canada", categories: ["weather", "alerts"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "possible", url: "https://api.weather.gc.ca/collections/marineweather-realtime", citation: 'Environment and Climate Change Canada, "Marine weather forecasts (experimental)," 2026. [Online]. Available: https://api.weather.gc.ca/collections/marineweather-realtime. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-NRCAN-EGS-FLOOD", name: "NRCan EGS near-real-time flood extent (SAR)", operator: "Natural Resources Canada — Emergency Geomatics Service", categories: ["flood"], geo: { level: "national" }, commercial: "yes", licence: "OGL-Canada", status: "possible", url: "https://geo.ca/flood-mapping/flood-map-gallery/floods-in-canada-current-year/", citation: 'Natural Resources Canada, "Emergency Geomatics Service flood product (RCM/Sentinel-1 SAR)," 2026. [Online]. Available: https://geo.ca/flood-mapping/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-GRCA", name: "Grand River Conservation Authority (KiWIS)", operator: "Grand River Conservation Authority", categories: ["level", "flow", "precip", "water-quality"], geo: { level: "provincial", province: "ON" }, commercial: "yes", licence: "GRCA Open Data", status: "possible", url: "https://waterdata.grandriver.ca/", citation: 'Grand River Conservation Authority, "Water data web services (KiWIS)," 2026. [Online]. Available: https://data.grandriver.ca/webservices-monitoring.html. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-ON-TRCA", name: "Toronto & Region Conservation Authority", operator: "Toronto and Region Conservation Authority", categories: ["level", "flow", "precip"], geo: { level: "municipal", province: "ON", city: "Toronto" }, commercial: "yes", licence: "TRCA Data Licence", status: "possible", url: "https://data.trca.ca/", citation: 'Toronto and Region Conservation Authority, "Real-time gauging data," 2026. [Online]. Available: https://data.trca.ca/dataset/trca-real-time-data. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-CITY-CALGARY", name: "City of Calgary river levels & flows", operator: "City of Calgary", categories: ["level", "flow", "water-quality"], geo: { level: "municipal", province: "AB", city: "Calgary" }, commercial: "yes", licence: "OGL-City of Calgary", status: "possible", url: "https://data.calgary.ca/", citation: 'City of Calgary, "River Levels and Flows (Open Data)," 2026. [Online]. Available: https://data.calgary.ca/Environment/River-Levels-and-Flows/5fdg-ifgr. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-CITY-EDMONTON", name: "City of Edmonton water levels & flows", operator: "City of Edmonton", categories: ["level", "flow"], geo: { level: "municipal", province: "AB", city: "Edmonton" }, commercial: "yes", licence: "OGL-City of Edmonton", status: "possible", url: "https://data.edmonton.ca/", citation: 'City of Edmonton, "Water Levels and Flows (Open Data)," 2026. [Online]. Available: https://data.edmonton.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-CITY-WINNIPEG", name: "City of Winnipeg river levels + CSO", operator: "City of Winnipeg", categories: ["level", "water-quality"], geo: { level: "municipal", province: "MB", city: "Winnipeg" }, commercial: "yes", licence: "OGL-City of Winnipeg", status: "possible", url: "https://data.winnipeg.ca/", citation: 'City of Winnipeg, "River Water Levels and CSO monitoring (Open Data)," 2026. [Online]. Available: https://data.winnipeg.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-CITY-TORONTO-BEACH", name: "City of Toronto beach water quality", operator: "City of Toronto", categories: ["water-quality", "recreation"], geo: { level: "municipal", province: "ON", city: "Toronto" }, commercial: "yes", licence: "OGL-Toronto", status: "possible", url: "https://open.toronto.ca/dataset/toronto-beaches-water-quality/", citation: 'City of Toronto, "Toronto Beaches Water Quality (Open Data)," 2026. [Online]. Available: https://open.toronto.ca/dataset/toronto-beaches-water-quality/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-CITY-MONTREAL-RSMA", name: "Montréal RSMA riverbank/beach water quality", operator: "Ville de Montréal", categories: ["water-quality", "recreation"], geo: { level: "municipal", province: "QC", city: "Montréal" }, commercial: "yes", licence: "CC-BY 4.0", status: "possible", url: "https://donnees.montreal.ca/dataset/rsma-qualite-de-l-eau-en-rive-qualo", citation: 'Ville de Montréal, "RSMA — qualité de l\'eau en rive (QUALO)," 2026. [Online]. Available: https://donnees.montreal.ca/dataset/rsma-qualite-de-l-eau-en-rive-qualo. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-METROVAN-BEACH", name: "Metro Vancouver beach water quality", operator: "Metro Vancouver", categories: ["water-quality", "recreation"], geo: { level: "municipal", province: "BC", city: "Vancouver" }, commercial: "yes", licence: "Metro Vancouver OGL", status: "possible", url: "https://www.bcbeach.fyi/", citation: 'Metro Vancouver, "Beach water-quality monitoring," 2026. [Online]. Available: https://metrovancouver.org/services/liquid-waste/beaches-and-recreational-water-quality-monitoring. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-HRM-BEACH", name: "Halifax beach water quality", operator: "Halifax Regional Municipality", categories: ["water-quality", "recreation"], geo: { level: "municipal", province: "NS", city: "Halifax" }, commercial: "yes", licence: "HRM Open Data", status: "possible", url: "https://data-hrm.hub.arcgis.com/", citation: 'Halifax Regional Municipality, "Beach Water Quality (Open Data)," 2026. [Online]. Available: https://data-hrm.hub.arcgis.com/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-AB-511-RWIS", name: "511 Alberta road-weather stations", operator: "Government of Alberta", categories: ["weather"], geo: { level: "provincial", province: "AB" }, commercial: "unknown", licence: "511 Alberta terms", status: "possible", url: "https://511.alberta.ca/developers/doc", citation: 'Government of Alberta, "511 Alberta weather-station API," 2026. [Online]. Available: https://511.alberta.ca/developers/doc. [Accessed: ' + ACCESSED + "].", note: "Requires a free developer key; air/pavement temp, wind, RH (no precip)." },
  { id: "SRC-YT-WATER", name: "Yukon Water Data Explorer", operator: "Government of Yukon", categories: ["level", "flow", "weather", "water-quality", "snow"], geo: { level: "provincial", province: "YT" }, commercial: "unknown", licence: "Yukon open data", status: "possible", url: "https://open.yukon.ca/data/water-data-explorer", citation: 'Government of Yukon, "Water Data Explorer," 2026. [Online]. Available: https://open.yukon.ca/data/water-data-explorer. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-NS-WATER", name: "Nova Scotia automated water quality + groundwater", operator: "Province of Nova Scotia", categories: ["water-quality", "groundwater"], geo: { level: "provincial", province: "NS" }, commercial: "yes", licence: "OGL-Nova Scotia", status: "possible", url: "https://novascotia.ca/nse/surface.water/automatedqualitymonitoring.asp", citation: 'Province of Nova Scotia, "Automated Surface Water Quality Monitoring," 2026. [Online]. Available: https://novascotia.ca/nse/surface.water/automatedqualitymonitoring.asp. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-PE-GW", name: "PEI near-real-time groundwater", operator: "Province of Prince Edward Island", categories: ["groundwater"], geo: { level: "provincial", province: "PE" }, commercial: "yes", licence: "OGL-PEI", status: "possible", url: "https://www.app.geo.ca/", citation: 'Province of Prince Edward Island, "Near-real-time groundwater network," 2026. [Online]. Available: https://www.app.geo.ca/. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-NB-RIVERWATCH", name: "New Brunswick River Watch + GeoNB flood", operator: "Government of New Brunswick", categories: ["flood", "level"], geo: { level: "provincial", province: "NB" }, commercial: "yes", licence: "OGL-New Brunswick", status: "possible", url: "https://www.gnb.ca/en/emergency/river-watch.html", citation: 'Government of New Brunswick, "River Watch and GeoNB flood mapping," 2026. [Online]. Available: https://www.gnb.ca/en/emergency/river-watch.html. [Accessed: ' + ACCESSED + "]." },
  { id: "SRC-SWIMGUIDE", name: "Swim Guide beach advisories", operator: "Swim Drink Fish", categories: ["recreation", "water-quality"], geo: { level: "national" }, commercial: "unknown", licence: "partner arrangement", status: "possible", url: "https://www.theswimguide.org/", citation: 'Swim Drink Fish, "Swim Guide," 2026. [Online]. Available: https://www.theswimguide.org/. [Accessed: ' + ACCESSED + "].", note: "Aggregates monitoring-agency data; API access by partner arrangement." },
  { id: "SRC-COCORAHS", name: "CoCoRaHS crowd-sourced precipitation", operator: "CoCoRaHS", categories: ["precip"], geo: { level: "national" }, commercial: "unknown", licence: "unconfirmed", status: "possible", url: "https://www.cocorahs.org/canada.aspx", citation: 'CoCoRaHS, "Community Collaborative Rain, Hail and Snow Network — Canada," 2026. [Online]. Available: https://www.cocorahs.org/canada.aspx. [Accessed: ' + ACCESSED + "].", note: "Volunteer daily precip; QC varies (crowd-sourced tier)." },
];

/** Three lifecycle statuses, in display order, with labels + dot colours. */
export const STATUS_META = {
  implemented: { label: "Implemented", blurb: "Live in the app, serving data now.", dot: "#10b981" },
  testing: { label: "Research & Testing", blurb: "Verified reachable; not yet wired into the app.", dot: "#f59e0b" },
  possible: { label: "Possible", blurb: "Identified candidate; not yet tested.", dot: "#94a3b8" },
};

/** 'ad-supported' when the licence permits commercial reuse, else 'ad-free'. */
export function surfaceFor(source) {
  return source.commercial === "yes" ? "ad-supported" : "ad-free";
}

export const PROVINCE_NAMES = {
  AB: "Alberta", BC: "British Columbia", MB: "Manitoba", NB: "New Brunswick",
  NL: "Newfoundland and Labrador", NS: "Nova Scotia", NT: "Northwest Territories",
  NU: "Nunavut", ON: "Ontario", PE: "Prince Edward Island", QC: "Québec",
  SK: "Saskatchewan", YT: "Yukon",
};

/**
 * Group sources geographically: National, then each Province (with its municipal
 * sources nested under `cities`). Returns a render-ready tree.
 */
export function groupByGeography(sources = SOURCES) {
  const national = [];
  const provinces = {};
  for (const s of sources) {
    if (s.geo.level === "national") {
      national.push(s);
      continue;
    }
    const code = s.geo.province || "Other";
    const p = (provinces[code] ||= { code, name: PROVINCE_NAMES[code] || code, provincial: [], cities: {} });
    if (s.geo.level === "municipal" && s.geo.city) {
      (p.cities[s.geo.city] ||= []).push(s);
    } else {
      p.provincial.push(s);
    }
  }
  const orderedProvinces = Object.values(provinces).sort((a, b) => a.name.localeCompare(b.name));
  return { national, provinces: orderedProvinces };
}

/** Stable IEEE reference numbering: assigns [n] in registry order. */
export function withRefNumbers(sources = SOURCES) {
  return sources.map((s, i) => ({ ...s, ref: i + 1 }));
}

/** Look up a source by id (for the future per-station source line). */
export function sourceById(id) {
  return SOURCES.find((s) => s.id === id) || null;
}
