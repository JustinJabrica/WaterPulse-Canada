"""
DS-STD-2026.1 — residual gentle stress harness (MANUAL launch).

Characterizes the safe sustainable request rate + failure signatures for the
few sources with NO sanctioned bulk/API (Alberta rivers.alberta.ca, Saskatchewan
htmlwidget, BC AQUARIUS) plus a tolerant Open-Meteo "too-fast" burst probe.
Gentle by design: graduated knee-finder (Alberta capped low), random 10–30 min
gaps, descriptive User-Agent + contact, honours Retry-After, no cache-bypass,
~10 h cap, aborts on sustained blocking, fully checkpointed.

RUN THIS YOURSELF (ideally from a non-production IP; pause the app's 10-min
scheduler first):

    # Validate the machinery fast (short gaps, tiny samples):
    docker compose run --rm -T --no-deps --entrypoint python backend -m tests.stress_test --smoke

    # The real overnight run (detached; runs for hours):
    docker compose run -d --name wp-stress --no-deps --entrypoint python backend \\
        -m tests.stress_test --targets ab,sk,bc,weather --max-hours 10

    docker stop wp-stress            # stop early (checkpoint + partial CSVs are on disk)
    # resume: pass the run_id printed at start
    docker compose run --rm -T --no-deps --entrypoint python backend \\
        -m tests.stress_test --resume <run_id>

Outputs: tests/logs/<run_id>/{requests.csv,bunches.csv,events.log,checkpoint.json,summary.md}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

from tests.stress.config import RunConfig
from tests.stress.metrics import run_id_now
from tests.stress.report import StressLog
from tests.stress.runner import run

_LOGS_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def main() -> int:
    ap = argparse.ArgumentParser(description="DS-STD-2026.1 residual gentle stress harness")
    ap.add_argument("--targets", default="ab,sk,bc,weather",
                    help="comma-separated: ab,sk,bc,weather")
    ap.add_argument("--smoke", action="store_true", help="fast validation: tiny ladder, ~2s gaps")
    ap.add_argument("--max-hours", type=float, default=10.0)
    ap.add_argument("--gap-min", type=float, default=600.0)
    ap.add_argument("--gap-max", type=float, default=1800.0)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--logs-dir", default=_LOGS_DEFAULT)
    ap.add_argument("--resume", help="run_id to resume (continues after its last checkpoint)")
    args = ap.parse_args()

    cfg = RunConfig(
        targets=[t.strip() for t in args.targets.split(",") if t.strip()],
        gap_min_s=args.gap_min, gap_max_s=args.gap_max, max_hours=args.max_hours,
        request_timeout=args.timeout, seed=args.seed, smoke=args.smoke,
    )

    resume_from = 0
    if args.resume:
        run_id = args.resume
        cp = os.path.join(args.logs_dir, run_id, "checkpoint.json")
        if os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                resume_from = int(json.load(f).get("processed", 0))
    else:
        run_id = run_id_now("stress")

    log = StressLog(run_id, args.logs_dir)
    print(f"[DS-STD-2026.1 residual] run_id={run_id}  targets={cfg.targets}  "
          f"smoke={cfg.smoke}  resume_from={resume_from}")
    print(f"[DS-STD-2026.1 residual] logs → {log.dir}")
    if not cfg.smoke:
        print("[DS-STD-2026.1 residual] LIVE run against government servers — "
              "gentle knee-finder with 10–30 min gaps; Ctrl-C/`docker stop` is safe.")

    summary = asyncio.run(run(cfg, log, resume_from=resume_from))
    print(f"\n[DS-STD-2026.1 residual] done: {summary['bunches']} bunches, "
          f"{summary['requests']} requests, aborted={summary['aborted']}")
    print(f"[DS-STD-2026.1 residual] safe-max: {summary['safe_max']}")
    print(f"[DS-STD-2026.1 residual] summary → {os.path.join(log.dir, 'summary.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
