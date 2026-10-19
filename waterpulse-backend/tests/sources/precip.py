"""
Precipitation nowcast / analysis / storm layers — ECCC GeoMet WMS (category="precip").

Antecedent + nowcast inputs that drive flash-flood risk and the "will it rain on
this stretch?" recreation read. All are gridded raster WMS layers on GeoMet
(point values via WMS GetFeatureInfo / WCS / GRIB2); we confirm the layer
families are advertised in the WMS GetCapabilities inventory via the shared
`_geomet` helper. The existing `eccc_climate.py` already probes the RDPA/CaPA
precip-accumulation *collection*; these add the near-real-time families:

  SRC-ECCC-RADAR     — RADAR_1KM_RRAI (rain rate) / _RSNO (snow), ~6-min cadence.
  SRC-ECCC-HRDPA     — HRDPA 2.5 km high-res deterministic precip analysis
                       ("rain that actually fell"; CaPA, gauge+radar+model merge).
  SRC-ECCC-LIGHTNING — Lightning_2.5km_Density (severe-storm / flash-flood signal).

Licence: ECCC MSC Data Servers End-use Licence (commercial OK, attribution
"Data Source: Environment and Climate Change Canada").
Docs: https://eccc-msc.github.io/open-data/msc-data/obs_radar/readme_radar_en/
      https://eccc-msc.github.io/open-data/msc-data/nwp_hrdpa/readme_hrdpa_en/
      https://eccc-msc.github.io/open-data/msc-data/lightning/readme_lightning-geomet_en/
"""
from __future__ import annotations

from tests.sources._base import ProbeContext
from tests.sources._geomet import probe_geomet_wms_layers
from tests.stress.metrics import TestResult
from tests.sources._base import register

LICENCE = "OGL-Canada / ECCC MSC End-use Licence"


@register(
    test_id="precip-eccc-radar",
    category="precip",
    source_id="SRC-ECCC-RADAR",
    label="ECCC GeoMet weather radar (RADAR_1KM rain/snow rate)",
    jurisdiction="CA",
    licence=LICENCE,
    commercial_ok="yes",
)
async def probe_radar(spec, ctx: ProbeContext) -> TestResult:
    return await probe_geomet_wms_layers(
        spec, ctx, match_keys=("RADAR_1KM",),
        notes="ECCC 1 km composite weather radar (rain-rate RRAI / snow RSNO)",
    )


@register(
    test_id="precip-eccc-hrdpa",
    category="precip",
    source_id="SRC-ECCC-HRDPA",
    label="ECCC GeoMet HRDPA 2.5km precip analysis (CaPA, 'rain that fell')",
    jurisdiction="CA",
    licence=LICENCE,
    commercial_ok="yes",
)
async def probe_hrdpa(spec, ctx: ProbeContext) -> TestResult:
    return await probe_geomet_wms_layers(
        spec, ctx, match_keys=("HRDPA",),
        notes="ECCC HRDPA 2.5 km high-res deterministic precip analysis (CaPA)",
    )


@register(
    test_id="precip-eccc-lightning",
    category="precip",
    source_id="SRC-ECCC-LIGHTNING",
    label="ECCC GeoMet lightning density (Lightning_2.5km)",
    jurisdiction="CA",
    licence=LICENCE,
    commercial_ok="yes",
)
async def probe_lightning(spec, ctx: ProbeContext) -> TestResult:
    return await probe_geomet_wms_layers(
        spec, ctx, match_keys=("LIGHTNING",),
        notes="ECCC lightning density (severe-storm / flash-flood signal)",
    )
