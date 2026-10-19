"""
DataStream.org OData v4 shared config — API key via the WP_DATASTREAM_API_KEY env var.

DataStream (The Gordon Foundation) is Canada's main open water-quality /
river-temperature aggregator. Its OData v4 Public API requires an `x-api-key`
request header; request a free key from https://datastream.org/en-ca/documentation/api
(~24 business-hour turnaround). A 401 without a key is the DOCUMENTED outcome,
not a broken URL. Published limits: 2 req/s, no parallel requests, 30 s timeout.

Set the key for a probe run via the environment, e.g.::

    WP_DATASTREAM_API_KEY=<key> docker compose run --rm -T --no-deps \
        -e WP_DATASTREAM_API_KEY --entrypoint python backend \
        -m tests.probe_sources --category waterquality

Licence is per-dataset (ODC-By / PDDL / OGL — all permit commercial use; ODC-By
and OGL require attribution + the dataset DOI).
"""
from __future__ import annotations

import os

ODATA_BASE = "https://api.datastream.org/v1/odata/v4"


def api_key() -> str | None:
    """The configured DataStream key, or None if unset/blank."""
    key = os.environ.get("WP_DATASTREAM_API_KEY", "").strip()
    return key or None


def have_key() -> bool:
    return api_key() is not None


def datastream_headers() -> dict:
    """`{"x-api-key": <key>}` when a key is configured, else `{}` (→ documented 401)."""
    key = api_key()
    return {"x-api-key": key} if key else {}
