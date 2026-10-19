"""
Drainage / watershed GIS — basin & hydrographic-network geometry (category="drainage").

These are the sanctioned bulk GIS catalogues that define *where water drains*:
gauge drainage basins, the national hydro network, and provincial watershed /
hydrography products. Almost all are catalogued on the federal Open Government
Portal, so the probe reads the CKAN action API for clean JSON metadata rather
than downloading multi-GB geodatabases:

    https://open.canada.ca/data/api/action/package_show?id=<uuid>
      -> json["result"]["resources"] = [{name, url, format}, ...]

The probe reports the advertised resource formats (fields_found), the number of
resources (record_count) and the first few download URLs (extra) — a low-load,
metadata-only retrievability check. No bulk geometry is downloaded.

Sources & licences (citation = each dataset's Open Government / catalogue page):
  (a) SRC-WSC-BASINS  WSC gauge drainage basin polygons (keyed to WSC
        STATION_NUMBER, the 2-digit-prefix replacement) — OGL-Canada, commercial OK.
        https://open.canada.ca/data/en/dataset/0c121878-ac23-46f5-95df-eb9960753375
  (b) SRC-NHN         National Hydro Network (NHN) — OGL-Canada, commercial OK.
        https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977
  (c) SRC-HYDROSHEDS  HydroSHEDS / HydroBASINS nested watershed polygons
        (Pfafstetter-coded) — HydroSHEDS Technical Documentation Licence,
        commercial OK. Landing page HTML retrievability check only.
        https://www.hydrosheds.org/products/hydrobasins
  (d) SRC-BC-FWA      BC Freshwater Atlas watershed boundaries — OGL-British
        Columbia, commercial OK. Federated open.canada record.
        https://open.canada.ca/data/en/dataset/ab758580-809d-4e11-bb2c-df02ac5465c9
  (e) SRC-QC-GRHQ     QC Geographie du reseau hydrographique du Quebec (GRHQ) —
        CC-BY 4.0 (Quebec), commercial OK.
        https://open.canada.ca/data/en/dataset/bfbdeb1d-8398-444b-ad78-ab81f9d14e60
  (f) SRC-ON-OIH      Ontario Integrated Hydrology (OIH) data — OGL-Ontario,
        commercial OK. Federated open.canada record.
        https://open.canada.ca/data/en/dataset/ef0c4387-38ce-4adc-b761-f0506b82564e
"""
from __future__ import annotations

from tests.sources._base import ProbeContext, http_probe, register
from tests.stress import classify
from tests.stress.http_client import build_client
from tests.stress.metrics import TestResult

# ── Open Government Portal CKAN action API ──────────────────────────
CKAN_ACTION = "https://open.canada.ca/data/api/action/package_show"

# Datasets catalogued on open.canada.ca (federal + federated provincial records).
# Each is probed metadata-only via package_show; the probe reads spec.source_id
# to look up the CKAN uuid + human notes below.
CKAN_SOURCES = [
    dict(
        test_id="drainage-wsc-basins-ca",
        source_id="SRC-WSC-BASINS",
        label="WSC gauge drainage basin polygons (national)",
        jurisdiction="CA",
        licence="OGL-Canada 2.0",
        commercial_ok="yes",
        ckan_id="0c121878-ac23-46f5-95df-eb9960753375",
        notes="gauge drainage-basin polygons keyed to WSC STATION_NUMBER "
              "(replaces the 2-digit basin prefix); pairs with HYDAT stations",
    ),
    dict(
        test_id="drainage-nhn-ca",
        source_id="SRC-NHN",
        label="National Hydro Network (NHN)",
        jurisdiction="CA",
        licence="OGL-Canada 2.0",
        commercial_ok="yes",
        ckan_id="a4b190fe-e090-4e6d-881e-b87956c07977",
        notes="NHN work-unit hydrography: watercourses, waterbodies, "
              "catchments/drainage areas at 1:50k",
    ),
    dict(
        test_id="drainage-bc-fwa-bc",
        source_id="SRC-BC-FWA",
        label="BC Freshwater Atlas watershed boundaries",
        jurisdiction="BC",
        licence="OGL-British Columbia 2.0",
        commercial_ok="yes",
        ckan_id="ab758580-809d-4e11-bb2c-df02ac5465c9",
        notes="federated open.canada record for the BC Freshwater Atlas "
              "watershed boundaries (source: BC Data Catalogue)",
    ),
    dict(
        test_id="drainage-qc-grhq-qc",
        source_id="SRC-QC-GRHQ",
        label="QC Geographie du reseau hydrographique du Quebec (GRHQ)",
        jurisdiction="QC",
        licence="CC-BY 4.0",
        commercial_ok="yes",
        ckan_id="bfbdeb1d-8398-444b-ad78-ab81f9d14e60",
        notes="Quebec hydrographic network / watershed geometry (GRHQ)",
    ),
    dict(
        test_id="drainage-on-oih-on",
        source_id="SRC-ON-OIH",
        label="Ontario Integrated Hydrology (OIH) data",
        jurisdiction="ON",
        licence="OGL-Ontario 1.0",
        commercial_ok="yes",
        ckan_id="ef0c4387-38ce-4adc-b761-f0506b82564e",
        notes="OIH watershed-generation package: enhanced watercourse, "
              "hydrology-enforced DEM, flow-direction grid, streamgrid",
    ),
]
_CKAN_CONF = {c["source_id"]: c for c in CKAN_SOURCES}


async def _ckan_probe(spec, ctx: ProbeContext) -> TestResult:
    """Metadata-only retrievability check via CKAN package_show.

    Reads spec.source_id to pick the dataset uuid, fetches the JSON metadata,
    and inventories the advertised resource formats + count + first URLs. Never
    downloads bulk geometry (files are GB-scale geodatabases).
    """
    conf = _CKAN_CONF[spec.source_id]
    ckan_id = conf["ckan_id"]
    endpoint = f"{CKAN_ACTION}?id={ckan_id}"
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        # uuid came from the upstream catalogue -> from_metadata=True (a 404 is
        # an upstream/catalogue gap, not a URL we mis-built).
        f = await http_probe(
            ctx, client, CKAN_ACTION, source_id=spec.source_id,
            category=spec.category, params={"id": ckan_id}, from_metadata=True,
            notes=f"CKAN package_show id={ckan_id}",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=endpoint,
                requests=recs,
            )
        try:
            data = f.json()
            if not isinstance(data, dict):
                raise ValueError("CKAN response was not a JSON object")
            if not data.get("success", False):
                return spec.result(
                    retrievable=False, reason_category=classify.PARSE_ERROR,
                    reason_detail="CKAN success=false", endpoint=endpoint,
                    sample=f.text[:800], requests=recs,
                )
            result = data.get("result", {}) or {}
            resources = result.get("resources", []) or []
            formats = sorted(
                {(r.get("format") or "").strip().upper()
                 for r in resources if isinstance(r, dict)} - {""}
            )
            urls = [
                r.get("url") for r in resources
                if isinstance(r, dict) and r.get("url")
            ][:5]
            title = result.get("title") or result.get("name") or ""
        except Exception as exc:  # malformed JSON / unexpected shape
            reason, detail = classify.classify_exception(exc)
            return spec.result(
                retrievable=False, reason_category=classify.PARSE_ERROR,
                reason_detail=detail, endpoint=endpoint,
                sample=f.text[:800], requests=recs,
            )

        f.record.records_parsed = len(resources)
        reason = classify.OK if resources else classify.OK_EMPTY
        return spec.result(
            retrievable=bool(resources), reason_category=reason, endpoint=endpoint,
            fields_found=formats, record_count=len(resources),
            latency_ms=f.record.latency_ms, sample=f.text[:800], requests=recs,
            notes=conf["notes"],
            extra={
                "ckan_id": ckan_id,
                "dataset_title": title,
                "resource_formats": formats,
                "first_resource_urls": urls,
            },
        )


# ── HydroSHEDS / HydroBASINS (non-CKAN, HTML landing page) ──────────
HYDROBASINS_URL = "https://www.hydrosheds.org/products/hydrobasins"
# Documented HydroBASINS attribute table (advertised in the technical docs).
HYDROBASINS_FIELDS = [
    "HYBAS_ID", "NEXT_DOWN", "NEXT_SINK", "MAIN_BAS", "DIST_SINK", "DIST_MAIN",
    "SUB_AREA", "UP_AREA", "PFAF_ID", "ENDO", "COAST", "ORDER", "SORT",
]


async def _hydrosheds_probe(spec, ctx: ProbeContext) -> TestResult:
    """Retrievability check for the HydroBASINS product page (HTML, not JSON).

    HydroSHEDS has no CKAN/API metadata endpoint; the bulk polygons download
    from the product page. We only confirm the sanctioned landing page is
    reachable and report the documented attribute schema.
    """
    recs = []
    async with build_client(timeout=ctx.request_timeout) as client:
        f = await http_probe(
            ctx, client, HYDROBASINS_URL, source_id=spec.source_id,
            category=spec.category, from_metadata=True,
            notes="HydroBASINS product landing page (HTML)",
        )
        recs.append(f.record)
        if not f.ok:
            return spec.result(
                retrievable=False, reason_category=f.record.reason_category,
                reason_detail=f.record.reason_detail, endpoint=HYDROBASINS_URL,
                requests=recs,
            )
        text = f.text or ""
        has_content = "hydrobasins" in text.lower()
        return spec.result(
            retrievable=True,
            reason_category=classify.OK if has_content else classify.OK_EMPTY,
            endpoint=HYDROBASINS_URL, fields_found=HYDROBASINS_FIELDS,
            latency_ms=f.record.latency_ms, sample=text[:800], requests=recs,
            notes="HTML landing page for HydroBASINS (Pfafstetter-coded nested "
                  "watershed polygons); bulk shapefiles via the product page",
            extra={"download_hint": HYDROBASINS_URL},
        )


# ── Registration ────────────────────────────────────────────────────
for _c in CKAN_SOURCES:
    register(
        test_id=_c["test_id"],
        category="drainage",
        source_id=_c["source_id"],
        label=_c["label"],
        jurisdiction=_c["jurisdiction"],
        licence=_c["licence"],
        commercial_ok=_c["commercial_ok"],
    )(_ckan_probe)

register(
    test_id="drainage-hydrosheds-hydrobasins",
    category="drainage",
    source_id="SRC-HYDROSHEDS",
    label="HydroSHEDS HydroBASINS nested watershed polygons",
    jurisdiction="CA",
    licence="HydroSHEDS Technical Documentation Licence",
    commercial_ok="yes",
)(_hydrosheds_probe)
