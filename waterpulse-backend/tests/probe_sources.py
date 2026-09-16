"""
DS-STD-2026.1 — sanctioned source-verification runner.

Runs the full matrix of SANCTIONED probes (safe, low-load: one bulk file / one
API page / one SQLite read per source) sequentially — polite to every upstream
— and writes full evidence to tests/logs/<run_id>/ (requests.csv, tests.csv,
coverage.csv, per-test JSON, coverage_summary.json).

Usage (inside the backend container)::

    docker-compose run --rm -w /app backend python -m tests.probe_sources
    docker-compose run --rm -w /app backend python -m tests.probe_sources --category historical
    docker-compose run --rm -w /app backend python -m tests.probe_sources --source SRC-HYDAT
    docker-compose run --rm -w /app backend python -m tests.probe_sources --include-residual   # also run scrape probes ONCE

Residual/scrape probes (sanctioned=False) are SKIPPED by default; they belong to
the user-launched gentle overnight harness (tests.stress_test).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time

from tests.matrix import load_all, summarize
from tests.sources._base import ProbeContext, ProbeSpec
from tests.stress import classify
from tests.stress.metrics import ResultLog, TestResult, run_id_now

_LOGS_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


async def _run_one(spec: ProbeSpec, ctx: ProbeContext) -> TestResult:
    try:
        return await spec.fn(spec, ctx)
    except Exception as exc:  # a probe must never crash the run
        reason, detail = classify.classify_exception(exc)
        return spec.result(
            retrievable=False,
            reason_category=reason if reason != classify.UNKNOWN else classify.PARSE_ERROR,
            reason_detail=f"probe raised: {detail}",
            notes="probe function raised — see reason_detail",
        )


async def _main_async(args) -> int:
    probes = load_all()
    if not args.include_residual:
        probes = [p for p in probes if p.sanctioned]
    if args.category:
        probes = [p for p in probes if p.category == args.category]
    if args.source:
        probes = [p for p in probes if p.source_id == args.source]
    if args.only:
        wanted = set(args.only.split(","))
        probes = [p for p in probes if p.test_id in wanted]

    probes.sort(key=lambda p: (p.category, p.source_id, p.test_id))

    run_id = run_id_now("probes")
    log = ResultLog(run_id, args.logs_dir)
    ctx = ProbeContext(
        log=log, run_id=run_id, sample_size=args.sample_size,
        request_timeout=args.timeout, cache_dir=args.cache_dir,
        allow_downloads=not args.no_downloads,
    )

    print(f"[DS-STD-2026.1] run_id={run_id}  probes={len(probes)}  "
          f"(residual {'INCLUDED' if args.include_residual else 'skipped'})")
    print(f"[DS-STD-2026.1] logs → {log.dir}\n")

    results: list[TestResult] = []
    t0 = time.perf_counter()
    for i, spec in enumerate(probes, 1):
        r = await _run_one(spec, ctx)
        log.write_result(r)
        results.append(r)
        mark = "OK " if r.retrievable else "XX "
        depth = f" depth={r.earliest_year}→{r.latest_year}" if r.earliest_year else ""
        nfields = f" fields={len(r.fields_found)}" if r.fields_found else ""
        print(f"  [{i:>3}/{len(probes)}] {mark}{r.category:<11} {r.source_id:<22} "
              f"{r.reason_category:<26}{nfields}{depth}")

    elapsed = round(time.perf_counter() - t0, 1)
    ok = sum(1 for r in results if r.retrievable)
    cov = {
        "run_id": run_id,
        "elapsed_seconds": elapsed,
        "total": len(results),
        "retrievable": ok,
        "failed": len(results) - ok,
        "matrix": summarize(load_all()),
        "by_reason": _count(results, lambda r: r.reason_category),
        "by_category_retrievable": _count(
            [r for r in results if r.retrievable], lambda r: r.category),
        "commercial_ok_counts": _count(results, lambda r: r.commercial_ok),
    }
    with open(os.path.join(log.dir, "coverage_summary.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, indent=2)

    print(f"\n[DS-STD-2026.1] {ok}/{len(results)} retrievable in {elapsed}s")
    print(f"[DS-STD-2026.1] reasons: {cov['by_reason']}")
    print(f"[DS-STD-2026.1] summary → {os.path.join(log.dir, 'coverage_summary.json')}")
    return 0


def _count(items, key) -> dict:
    out: dict = {}
    for it in items:
        k = key(it)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> int:
    ap = argparse.ArgumentParser(description="DS-STD-2026.1 sanctioned source probes")
    ap.add_argument("--category", help="only this category (historical, current, stations, weather, aqi, watertemp, precip, snow, ice, drainage, groundwater, flood)")
    ap.add_argument("--source", help="only this source_id (e.g. SRC-HYDAT)")
    ap.add_argument("--only", help="comma-separated test_ids to run")
    ap.add_argument("--include-residual", action="store_true", help="also run scrape/residual probes ONCE (normally harness-only)")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--sample-size", type=int, default=3)
    ap.add_argument("--no-downloads", action="store_true", help="skip multi-MB downloads (HYDAT, CanSWE); report as skipped")
    ap.add_argument("--cache-dir", default="/tmp/wp-ds-cache")
    ap.add_argument("--logs-dir", default=_LOGS_DEFAULT)
    return asyncio.run(_main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
