/**
 * methodologyContent — the layered prose for the /methodology living-doc page.
 * Each section renders a plain-language `summary` (always visible) plus an
 * expandable `detail` ("How it's calculated / how reliable"). `refs` lists the
 * sourceRegistry ids the section relies on (the page links them to #sources).
 *
 * Content is faithful to the implementation: percentile thresholds and the
 * 5-year window match waterpulse-backend/app/services/readings_refresh.py; the
 * reliability tiers and safety language follow the DS-STD-2026.3 research.
 *
 * Keep numbers here in sync with the backend if the computation changes.
 */

export const SECTIONS = [
  {
    id: "conditions",
    title: "How we measure conditions",
    summary:
      "Most numbers you see — water level, flow, temperature, air quality — are measured by government agencies and passed through to you. We don't invent readings; we collect, label, and present them.",
    detail: [
      {
        h: "Water level & flow",
        body:
          "Level and flow come from Environment and Climate Change Canada / the Water Survey of Canada, plus provincial networks where they run their own gauges. One important thing to understand: flow (discharge) is almost never measured directly — it's calculated from the measured water level using a station-specific “rating curve.” That curve is most uncertain at very high water and can be thrown off when ice forms, so winter flow values are the least certain and are often flagged as estimated or revised later.",
      },
      {
        h: "Real-time vs. validated",
        body:
          "Real-time readings are “provisional” — best-available and subject to revision. Agencies later quality-check them (a flag that rises from preliminary → reviewed → checked → approved) and publish the final, validated record months to a year or more later. We show the latest available value and stamp it with when it was read.",
      },
      {
        h: "Reservoir capacity",
        body:
          "“% full” for reservoirs is reported directly by the operating agency (currently the Government of Alberta for Alberta reservoirs) — we display their figure, we don't compute it ourselves.",
      },
      {
        h: "Water temperature & water quality",
        body:
          "Water quality in Canada is overwhelmingly lab-analyzed grab samples taken periodically, not continuous live sensors. So a water-quality value is best read as “latest sample + trend,” not a live reading, and its reliability varies by the program that collected it.",
      },
      {
        h: "Weather & air quality",
        body:
          "Weather and air-quality figures are forecasts/analyses from meteorological providers, passed through and interpreted for display. Note a scale caveat: our current air-quality number is the US AQI (0–500); Canada's own index is the AQHI (1–10+), a combined health-risk measure of ozone, NO₂ and fine particulate — we are moving toward AQHI for Canadian relevance.",
      },
    ],
    refs: ["SRC-ECCC-DATAMART", "SRC-ECCC-GEOMET", "SRC-AB-RIVERS", "SRC-OPEN-METEO", "SRC-OPEN-METEO-AQI", "SRC-ECCC-AQHI"],
  },
  {
    id: "ratings",
    title: "How we calculate ratings (very low → very high)",
    summary:
      "A rating tells you whether today's reading is unusual for this station at this time of year — by comparing it to the same station's own history, not to other rivers.",
    detail: [
      {
        h: "The method",
        body:
          "For a station we gather its historical daily values within a ±7-day window around today's calendar date (so, mid-June is compared against past mid-Junes), pool those values across the years we hold, and find where today's reading falls as a percentile of that history.",
      },
      {
        h: "The bands",
        bullets: [
          "below the 10th percentile → very low",
          "10th–25th → low",
          "25th–75th → average",
          "75th–90th → high",
          "above the 90th percentile → very high",
        ],
      },
      {
        h: "Why some stations show no rating",
        body:
          "If we hold fewer than 5 historical values for that window, we show no rating rather than a misleading one. New stations, or stations with sparse history, will often have no rating until more data accrues.",
      },
      {
        h: "A current limitation, by design",
        body:
          "At this development stage we retain a 5-year history window. The established convention (e.g. USGS WaterWatch) uses 30+ years and bands of <10 / 10–25 / 25–75 / 75–90 / >90. Our 5-year window is a deliberate current-stage simplification — it makes ratings available now, but with wider uncertainty on the extremes. Our goal is to retain the full available record (federal archives reach back to the 1800s), which will make these ratings steadily more reliable.",
      },
    ],
    refs: ["SRC-HYDAT", "SRC-ECCC-GEOMET-DAILY"],
  },
  {
    id: "predictions",
    title: "How predictions work",
    summary:
      "WaterPulse is not a flood-warning authority. For anything predictive we point you to — and mirror — the official issuers, and we are explicit about what is a forecast versus an observation.",
    detail: [
      {
        h: "Flood warnings",
        body:
          "Official flood warnings and advisories are issued by ECCC and provincial river-forecast centres. WaterPulse surfaces and links those official alerts; it does not replace them or issue its own. Where a warning exists for your area, we show all of them — we never suppress an official alert.",
      },
      {
        h: "Streamflow forecasts",
        body:
          "Canada's national hydrological model (ECCC's NSRPS/DHPS) produces river-discharge forecasts out to ~6 days over part of the country, as a model grid — not a guaranteed per-point number. A forecast's uncertainty compounds rainfall-forecast error, snowpack/soil-moisture error and routing error, and is largest for small flashy basins, snowmelt peaks, and regulated (dammed) rivers. We label any forecast as such, with its issue time and horizon.",
      },
      {
        h: "Our own prediction, phased",
        body:
          "Our roadmap adds predictions in stages: first surfacing official feeds, then a transparent WaterPulse risk heuristic (percentile rating + trend + recent/forecast precipitation + snowpack), and only later a full model. Any WaterPulse-derived signal will be clearly labelled as our estimate, separate from official values.",
      },
    ],
    refs: ["SRC-ECCC-CAP", "SRC-ECCC-WATERPRED", "SRC-BC-RFC", "SRC-QC-VIGILANCE"],
  },
  {
    id: "recommendations",
    title: "How recommendations work",
    summary:
      "Recommendations — like whether it's a nice day for the river — are advisory conveniences that combine conditions. They are never a safety guarantee.",
    detail: [
      {
        h: "Recreation suitability (planned)",
        body:
          "A planned “good day on the river?” read will combine weather (temperature, wind, precipitation, UV), air quality and wildfire smoke, water temperature, flow safety, and swim-safety water quality (E. coli / cyanobacteria where available).",
      },
      {
        h: "Advisory only, conservatively gated",
        body:
          "Any such recommendation is advisory only and will be gated conservatively: it will not turn “green” on stale, modeled, or crowd-sourced data, and it will always surface the uncertainty rather than hide it. Conditions like bacteria after rain, cold-water shock, hydraulics, debris and rising provisional flow can change faster than any data feed.",
      },
    ],
    refs: ["SRC-OPEN-METEO", "SRC-ECCC-FIREWORK", "SRC-DATASTREAM-WQ"],
  },
  {
    id: "reliability",
    title: "How reliable is it?",
    summary:
      "Not all data is equally certain. We tier every value by how it was produced, and we try to show that tier rather than bury it.",
    detail: [
      {
        h: "Our reliability tiers (most → least certain)",
        bullets: [
          "Observed – validated: agency-approved, quality-controlled records. Safe for history and trends.",
          "Observed – provisional: real-time readings, subject to revision (and least certain for ice-affected winter flow).",
          "Official forecast / model: ECCC model forecasts and analyses — a best estimate with a horizon, not a guarantee.",
          "Derived / modeled: our percentile ratings, and modeled attributes like a river's long-term average size — estimates, not current measurements.",
          "Crowd-sourced: volunteer or user reports — useful context, never an automatic safety signal.",
        ],
      },
      {
        h: "What we show you",
        body:
          "Every reading carries when it was last updated. Where data is provisional, ice-affected, estimated, or modeled, our aim is to say so plainly and, when data is stale or a station's record is too short, to widen or withhold a rating rather than show false confidence.",
      },
    ],
    refs: ["SRC-HYDAT", "SRC-ECCC-DATAMART", "SRC-HYDRORIVERS"],
  },
  {
    id: "safety",
    title: "Safety & limitations",
    summary:
      "WaterPulse is an information tool, not an emergency service. Never base a safety decision solely on this app.",
    detail: [
      {
        body:
          "Flow, level, forecast and water-quality values here are not a substitute for official warnings or for your own on-site judgment. For flood or emergency decisions, rely on ECCC, your provincial river-forecast centre, and local emergency management — we mirror their warnings but are not an authoritative source.",
      },
      {
        body:
          "Swim and recreation suitability is advisory only. Water-quality data is point-in-time and drawn from many programs of differing rigour, and real conditions (bacteria after rainfall, cold-water shock, currents, debris, rapidly rising provisional flow) can change faster than any feed. Never make evacuation, driving, swimming, or other safety decisions based solely on information from WaterPulse.",
      },
    ],
    refs: [],
  },
];
