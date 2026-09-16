"""
Residual gentle-harness configuration + target registry.

Only the sources that have NO sanctioned bulk/API and must be scraped/polled:
Alberta (rivers.alberta.ca per-station JSON), Saskatchewan (wsask.ca hydrograph
htmlwidget), BC (AQUARIUS undocumented), plus Open-Meteo as the tolerant target
for the "requested too fast" bad-input burst. This harness characterizes the
SAFE sustainable rate + failure signatures — it never floods.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Representative WSC/provincial station samples (avoid depending on the very
#    discovery endpoints that refuse connections). Real WSC IDs. ──────────────
AB_STATIONS = [
    "05BN002", "05AD940", "07NB001", "07DD007", "05AE002", "05BJ008", "05AA004",
    "05BB001", "05CE002", "07FD009", "05DE006", "05CG004", "11AA005", "05BH016",
    "07OB003",
]
SK_STATIONS = [
    "05MB006", "05JG006", "05HG001", "05KJ001", "05GG001", "05AK001", "05JF001",
    "05HD036", "06AD006", "05FE004", "05GC001", "05JM001", "05AG006", "05LC001",
    "05KD003",
]
BC_STATIONS = [
    "08MF005", "08NM116", "08HB048", "08MH006", "08GA010", "08NL071", "08LG048",
    "08NE077", "08KA004", "08HD006", "08MG005", "08NN013", "08JB002", "08OA004",
    "08HA011",
]
# Open-Meteo coordinate tokens (lat,lon) spread across Canada — seeded, static.
WEATHER_COORDS = [
    "51.05,-114.07", "49.28,-123.12", "53.55,-113.49", "43.65,-79.38",
    "45.50,-73.57", "46.81,-71.21", "44.65,-63.57", "47.56,-52.71",
    "60.72,-135.05", "62.45,-114.37", "50.45,-104.61", "49.90,-97.14",
    "48.43,-89.25", "68.36,-133.72", "52.13,-106.67",
]


@dataclass
class Target:
    key: str
    label: str
    host: str
    licence: str
    commercial_ok: str
    tokens: list[str]                 # stations / coords to vary the request
    url_builder: callable             # (token) -> url
    from_metadata: bool = False
    cap: int = 16                     # per-host concurrency ceiling (gentle)
    bad_path: str = ""                # a deliberately-wrong URL for the bad-path probe


def _ab_url(tok: str) -> str:
    return ("https://rivers.alberta.ca/apps/Basins/data/figures/river/abrivers/"
            f"stationdata/R_HG_{tok}_table.json")


def _sk_url(tok: str) -> str:
    return f"https://www.wsask.ca/hydrographs/{tok}-hrly.html"


def _bc_url(tok: str) -> str:
    # AQUARIUS WebPortal export/JSON is undocumented; probe a plausible dataset
    # listing repeatedly to characterize concurrency tolerance.
    return f"https://bcmoe-prod.aquaticinformatics.net/Data/Data_List?station={tok}"


def _weather_url(tok: str) -> str:
    lat, lon = tok.split(",")
    return ("https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m")


TARGETS: dict[str, Target] = {
    "ab": Target(
        key="ab", label="Alberta rivers.alberta.ca per-station JSON",
        host="rivers.alberta.ca", licence="GoA copyright (non-commercial)",
        commercial_ok="no-written-permission", tokens=AB_STATIONS,
        url_builder=_ab_url, cap=16,
        bad_path="https://rivers.alberta.ca/apps/Basins/data/figures/river/abrivers/stationdata/DOES_NOT_EXIST.json",
    ),
    "sk": Target(
        key="sk", label="Saskatchewan wsask.ca hydrograph htmlwidget",
        host="www.wsask.ca", licence="SK Crown copyright (non-commercial)",
        commercial_ok="no-written-permission", tokens=SK_STATIONS,
        url_builder=_sk_url, cap=16,
        bad_path="https://www.wsask.ca/hydrographs/99ZZ999-hrly.html",
    ),
    "bc": Target(
        key="bc", label="BC AQUARIUS WebPortal (undocumented export/JSON)",
        host="bcmoe-prod.aquaticinformatics.net", licence="OGL-BC",
        commercial_ok="yes", tokens=BC_STATIONS, url_builder=_bc_url, cap=16,
        bad_path="https://bcmoe-prod.aquaticinformatics.net/Data/DOES_NOT_EXIST",
    ),
    "weather": Target(
        key="weather", label="Open-Meteo forecast (rapid-burst tolerance probe)",
        host="api.open-meteo.com", licence="CC-BY-4.0 (non-commercial free tier)",
        commercial_ok="non-commercial", tokens=WEATHER_COORDS,
        url_builder=_weather_url, cap=32,
        bad_path="https://api.open-meteo.com/v1/forecast?latitude=999&longitude=999&current=temperature_2m",
    ),
}


@dataclass
class RunConfig:
    targets: list[str] = field(default_factory=lambda: ["ab", "sk", "bc", "weather"])
    ladder: list[int] = field(default_factory=lambda: [1, 2, 4, 8, 16])
    gap_min_s: float = 600.0          # 10 min
    gap_max_s: float = 1800.0         # 30 min
    max_hours: float = 10.0
    request_timeout: float = 45.0
    jitter_ms: tuple = (50, 250)      # per-request start jitter within a bunch
    knee_error_rate: float = 0.10     # stop a target's ladder past this throttle rate
    abort_block_rate: float = 0.90    # canary + abort if a bunch is this blocked
    rapid_burst_n: int = 25           # "requested too fast" probe size (weather only)
    seed: int = 1234
    smoke: bool = False               # smoke: tiny ladder, ~2s gaps, 1-token samples

    def gap_bounds(self) -> tuple[float, float]:
        return (1.0, 3.0) if self.smoke else (self.gap_min_s, self.gap_max_s)

    def effective_ladder(self, cap: int) -> list[int]:
        lad = [2, 4] if self.smoke else self.ladder
        return [c for c in lad if c <= cap] or [1]
