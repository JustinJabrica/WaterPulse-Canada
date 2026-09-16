"""
Shared HTTP client factory for the DS-STD-2026.1 suite.

Anti-flag / good-citizen defaults (aligned with the MSC Open Data Service
Usage Policy and MET Norway ToS):
  - a descriptive, contactable User-Agent (identifies us as legitimate),
  - a bounded connection pool (no socket churn that looks abusive),
  - NO cache-bypass headers (MSC policy forbids Cache-Control: no-cache),
  - follow redirects (several gov hosts 30x to canonical URLs).
"""
from __future__ import annotations

import httpx

# Descriptive UA with contact — MSC policy asks for a "meaningful User-Agent";
# MET Norway ToS *requires* an identifying UA with contact info.
USER_AGENT = (
    "WaterPulse-Canada/1.0 (public-good hydrometric data-source diagnostic; "
    "contact: justin.jabrica@shaw.ca)"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}


def build_client(
    timeout: float = 60.0,
    *,
    connect_timeout: float | None = None,
    max_connections: int = 8,
    follow_redirects: bool = True,
    extra_headers: dict | None = None,
) -> httpx.AsyncClient:
    """Create an AsyncClient with WaterPulse's polite defaults.

    A short connect timeout surfaces `connect_refused`/`connect_timeout`
    quickly (rather than hanging on the full read timeout) — important for
    characterizing the Alberta connection-refusal behaviour.
    """
    headers = dict(DEFAULT_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            timeout,
            connect=connect_timeout if connect_timeout is not None else min(15.0, timeout),
        ),
        headers=headers,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max(2, max_connections // 2),
        ),
        follow_redirects=follow_redirects,
    )
