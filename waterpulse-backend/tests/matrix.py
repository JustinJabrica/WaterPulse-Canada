"""
Declarative test-matrix registry.

Auto-discovers every module in `tests/sources/` (except private `_*`) so their
`@register(...)` decorators populate the shared REGISTRY. Add a new source =
drop a new `tests/sources/<name>.py`; no edit here required.
"""
from __future__ import annotations

import importlib
import pkgutil

import tests.sources as _sources_pkg
from tests.sources._base import REGISTRY, ProbeSpec


def load_all() -> list[ProbeSpec]:
    """Import every source module so all probes self-register, then return them."""
    for mod in pkgutil.iter_modules(_sources_pkg.__path__):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"tests.sources.{mod.name}")
    return REGISTRY


def summarize(probes: list[ProbeSpec]) -> dict:
    """Counts by category and sanctioned/residual split — for Part 2."""
    by_cat: dict[str, int] = {}
    sanctioned = residual = 0
    for p in probes:
        by_cat[p.category] = by_cat.get(p.category, 0) + 1
        if p.sanctioned:
            sanctioned += 1
        else:
            residual += 1
    return {
        "total": len(probes),
        "sanctioned": sanctioned,
        "residual": residual,
        "by_category": dict(sorted(by_cat.items())),
    }
