"""
Graduated knee-finder for the residual gentle harness.

One "bunch" = one concurrency level against one target, then a random 10–30 min
gap. Ramp concurrency (capped low, esp. Alberta) until throttling starts (the
knee), then stop that target's ladder. Labelled bad-input probes (invalid
station, bad path, and one rapid burst on Open-Meteo) capture failure
signatures. Aborts the whole run if a target is sustained-blocked (canary check
after a gap). Everything is checkpointed for --resume.
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

from tests.sources._base import http_probe
from tests.stress import classify
from tests.stress.config import TARGETS, RunConfig, Target
from tests.stress.http_client import build_client
from tests.stress.metrics import RequestRecord
from tests.stress.report import StressLog, bunch_stats_from


@dataclass
class Bunch:
    target: str
    concurrency: int
    kind: str      # ladder | invalid | badpath | rapidburst
    label: str


def build_schedule(cfg: RunConfig) -> list[Bunch]:
    sched: list[Bunch] = []
    for key in cfg.targets:
        t = TARGETS[key]
        for c in cfg.effective_ladder(t.cap):
            sched.append(Bunch(key, c, "ladder", f"{key} ladder c={c}"))
    for key in cfg.targets:
        if key in ("ab", "sk"):
            sched.append(Bunch(key, 1, "invalid", f"{key} invalid-station"))
        sched.append(Bunch(key, 1, "badpath", f"{key} bad-path"))
    if "weather" in cfg.targets:
        n = 5 if cfg.smoke else cfg.rapid_burst_n
        sched.append(Bunch("weather", n, "rapidburst", "weather rapid-burst (too-fast signature)"))
    return sched


def _urls_for(cfg: RunConfig, t: Target, bunch: Bunch) -> list[str]:
    if bunch.kind == "invalid":
        return [t.url_builder("99ZZ999")]
    if bunch.kind == "badpath":
        return [t.bad_path]
    toks = t.tokens
    return [t.url_builder(toks[i % len(toks)]) for i in range(bunch.concurrency)]


async def _fire(cfg: RunConfig, t: Target, urls: list[str], concurrency: int,
                kind: str, rng: random.Random) -> list[RequestRecord]:
    sem = asyncio.Semaphore(concurrency)
    recs: list[RequestRecord] = []
    jlo, jhi = cfg.jitter_ms

    async def one(url: str):
        async with sem:
            if kind != "rapidburst":  # the deliberate burst intentionally has no jitter
                await asyncio.sleep(rng.uniform(jlo, jhi) / 1000.0)
            # invalid-station = a valid URL shape with a bogus station (upstream gap);
            # bad-path = a URL WE deliberately malformed (our address mistake).
            f = await http_probe(None, client, url, source_id=f"RESIDUAL-{t.key.upper()}",
                                 category="residual", from_metadata=(kind == "invalid"),
                                 notes=kind, retries=0)  # pristine: no retry masking of throttle/refusal
            recs.append(f.record)

    async with build_client(timeout=cfg.request_timeout,
                            max_connections=max(2, concurrency)) as client:
        await asyncio.gather(*[one(u) for u in urls], return_exceptions=True)
    return recs


def _rate(recs: list[RequestRecord], reasons: set) -> float:
    return sum(1 for r in recs if r.reason_category in reasons) / len(recs) if recs else 0.0


async def run(cfg: RunConfig, log: StressLog, resume_from: int = 0) -> dict:
    rng = random.Random(cfg.seed)
    schedule = build_schedule(cfg)
    gmin, gmax = cfg.gap_bounds()
    knee_hit: set[str] = set()
    blocked_targets: set[str] = set()
    consecutive_block = 0
    safe_max: dict[str, int] = {}
    reason_totals: dict[str, int] = {}
    total_req = 0
    aborted = False
    ran_any = resume_from > 0
    processed = 0
    bunch_id = 0
    t_start = time.monotonic()
    log.event(f"start targets={cfg.targets} scheduled={len(schedule)} smoke={cfg.smoke} resume_from={resume_from}")

    for bunch in schedule:
        processed += 1
        if processed <= resume_from:
            continue
        if (time.monotonic() - t_start) > cfg.max_hours * 3600:
            log.event("time cap reached — stopping")
            break
        if bunch.kind == "ladder" and bunch.target in knee_hit:
            continue

        if ran_any:
            gap = rng.uniform(gmin, gmax)
            log.event(f"gap {gap:.0f}s before [{processed}/{len(schedule)}] {bunch.label}")
            await asyncio.sleep(gap)
        ran_any = True
        bunch_id += 1

        t = TARGETS[bunch.target]
        urls = _urls_for(cfg, t, bunch)
        w0 = time.monotonic()
        recs = await _fire(cfg, t, urls, bunch.concurrency, bunch.kind, rng)
        wall = time.monotonic() - w0
        log.record_requests(recs)
        total_req += len(recs)
        for r in recs:
            reason_totals[r.reason_category] = reason_totals.get(r.reason_category, 0) + 1

        stat = bunch_stats_from(recs, bunch_id=bunch_id, target=bunch.target,
                                kind=bunch.kind, concurrency=bunch.concurrency, wall_s=wall)
        stat.notes = bunch.label
        throttle = _rate(recs, classify.THROTTLE_REASONS)
        if bunch.kind == "ladder":
            if throttle >= cfg.knee_error_rate:
                stat.knee = True
                knee_hit.add(bunch.target)
                log.event(f"KNEE {bunch.target} c={bunch.concurrency} throttle={throttle:.0%}")
            else:
                safe_max[bunch.target] = bunch.concurrency
        log.write_bunch(stat)
        log.event(f"[{processed}/{len(schedule)}] {bunch.label}: "
                  f"{stat.n_ok}/{stat.n_req} ok, {stat.throughput_req_s} req/s, "
                  f"reasons={stat.reason_breakdown}")

        block = _rate(recs, {classify.CONNECT_REFUSED, classify.HTTP_403})
        if block >= cfg.abort_block_rate:
            log.event(f"BLOCK {block:.0%} on {bunch.target} — canary after a gap")
            await asyncio.sleep(rng.uniform(gmin, gmax))
            canary = await _fire(cfg, t, [t.url_builder(t.tokens[0])], 1, "ladder", rng)
            log.record_requests(canary)
            if canary and canary[0].reason_category in {classify.CONNECT_REFUSED, classify.HTTP_403}:
                # Per-target skip: stop hammering THIS target but keep covering the
                # others (a touchy portal like Alberta must not abort the whole run).
                knee_hit.add(bunch.target)
                blocked_targets.add(bunch.target)
                consecutive_block += 1
                log.event(f"TARGET BLOCKED — skipping remaining {bunch.target} bunches "
                          f"(consecutive blocked bunches={consecutive_block})")
                if consecutive_block >= 3:
                    aborted = True
                    log.event("ABORT — 3+ consecutive blocked bunches across targets "
                              "(IP-wide throttle suspected); stopping run")
                    break
                continue
            log.event("canary recovered — continuing")
        else:
            consecutive_block = 0

        log.checkpoint({"run_id": log.run_id, "processed": processed,
                        "bunches_run": bunch_id, "knee_hit": sorted(knee_hit),
                        "safe_max": safe_max, "aborted": aborted})

    elapsed = round(time.monotonic() - t_start, 1)
    summary = {
        "run_id": log.run_id, "elapsed_seconds": elapsed, "bunches": bunch_id,
        "requests": total_req, "aborted": aborted, "safe_max": safe_max,
        "knee_hit": sorted(knee_hit), "blocked_targets": sorted(blocked_targets),
        "reason_totals": dict(sorted(reason_totals.items(), key=lambda kv: -kv[1])),
    }
    log.write_summary(summary)
    log.event(f"done bunches={bunch_id} requests={total_req} elapsed={elapsed}s aborted={aborted}")
    return summary
