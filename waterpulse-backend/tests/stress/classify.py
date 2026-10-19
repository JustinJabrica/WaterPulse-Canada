"""
Failure-reason classifier — the forensic core.

Maps an HTTP status or an exception to one canonical reason category so
Report 3 can catalogue *why* each source/request succeeds or fails
(wrong address vs wrong station vs throttled vs upstream-missing vs timeout).
"""
from __future__ import annotations

import httpx

# ── Canonical reason categories ─────────────────────────────────────
OK = "ok"                                   # 2xx with parseable, non-empty data
OK_EMPTY = "ok_empty"                        # 2xx but zero records
HTTP_404_UPSTREAM_MISSING = "http_404_upstream_missing"  # URL came from upstream metadata
HTTP_404_BAD_PATH = "http_404_bad_path"      # URL we constructed → our mistake
HTTP_400 = "http_400_bad_request"
HTTP_401 = "http_401_unauthorized"           # missing/invalid API key
HTTP_403 = "http_403_forbidden"              # blocked / bot-protection
HTTP_429 = "http_429_rate_limited"
HTTP_5XX = "http_5xx_server"
HTTP_OTHER = "http_other_status"
CONNECT_REFUSED = "connect_refused"          # "All connection attempts failed"
CONNECT_TIMEOUT = "connect_timeout"
READ_TIMEOUT = "read_timeout"
DNS_ERROR = "dns_error"
TLS_ERROR = "tls_error"
INVALID_STATION = "invalid_station"          # id absent from the source's station list
PARSE_ERROR = "parse_error"                  # bytes returned but unparseable
UNKNOWN = "unknown"

SUCCESS_REASONS = {OK, OK_EMPTY}
# Reasons that indicate throttling/blocking (used by the knee-finder + abort logic)
THROTTLE_REASONS = {CONNECT_REFUSED, CONNECT_TIMEOUT, READ_TIMEOUT, HTTP_429, HTTP_5XX, HTTP_403}

_DNS_HINTS = (
    "name or service not known", "nodename nor servname", "getaddrinfo",
    "temporary failure in name resolution", "no address associated",
    "name does not resolve",
)


def classify_status(status_code: int, from_metadata: bool = False) -> str:
    """Classify an HTTP status. `from_metadata` distinguishes a 404 on a URL
    the upstream advertised (data gap) from a 404 on a URL we built (our bug)."""
    if 200 <= status_code < 300:
        return OK
    if status_code == 400:
        return HTTP_400
    if status_code == 401:
        return HTTP_401
    if status_code == 403:
        return HTTP_403
    if status_code == 404:
        return HTTP_404_UPSTREAM_MISSING if from_metadata else HTTP_404_BAD_PATH
    if status_code == 429:
        return HTTP_429
    if 500 <= status_code < 600:
        return HTTP_5XX
    return HTTP_OTHER


def classify_exception(exc: BaseException) -> tuple[str, str]:
    """Return (reason_category, detail) for a transport/parse exception."""
    detail = f"{type(exc).__name__}: {exc}"
    msg = str(exc).lower()

    if isinstance(exc, (httpx.ConnectTimeout,)):
        return CONNECT_TIMEOUT, detail
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return READ_TIMEOUT, detail
    if isinstance(exc, httpx.ConnectError):
        if any(h in msg for h in _DNS_HINTS):
            return DNS_ERROR, detail
        # anyio raises "All connection attempts failed" on refusal/unreachable
        return CONNECT_REFUSED, detail
    if isinstance(exc, httpx.ProxyError):
        return CONNECT_REFUSED, detail
    if isinstance(exc, httpx.TimeoutException):
        return READ_TIMEOUT, detail
    if "certificate" in msg or "ssl" in msg or "tls" in msg:
        return TLS_ERROR, detail
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return PARSE_ERROR, detail
    if isinstance(exc, httpx.HTTPError):
        return UNKNOWN, detail
    return UNKNOWN, detail
