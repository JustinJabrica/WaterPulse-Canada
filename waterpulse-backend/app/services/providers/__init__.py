"""
Provider Registry
==================
Central list of active data providers. Orchestrators import
get_active_providers() and loop through them — no hardcoded
provider references anywhere else.

To add a new provider (e.g. BC, SK):
    1. Create providers/bc_provider.py implementing BaseProvider
    2. Add one line to _PROVIDERS below
"""

from app.services.providers.base_provider import BaseProvider
from app.services.providers.eccc_provider import ECCCProvider
from app.services.providers.alberta_provider import AlbertaProvider


# Providers run in this order. For shared stations, first write wins.
# Alberta runs first so its richer fields (precipitation, capacity,
# station type) take priority over ECCC's.
_PROVIDERS: list[BaseProvider] = [
    AlbertaProvider(),
    ECCCProvider(),
]


def get_active_providers() -> list[BaseProvider]:
    """Return all registered providers in priority order."""
    return _PROVIDERS
