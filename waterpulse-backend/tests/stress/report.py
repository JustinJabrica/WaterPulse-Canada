"""Evidence logging for the residual gentle harness: per-request CSV,
per-bunch CSV, an events timeline, a resumable checkpoint, and a summary."""
from __future__ import annotations

import csv
import json
import os
import statistics
from dataclasses import asdict, dataclass, field

from tests.stress.metrics import REQUEST_COLUMNS, RequestRecord, utcnow_iso

BUNCH_COLUMNS = [
    "bunch_id", "ts_utc", "target", "kind", "concurrency", "n_req", "n_ok",
    "n_fail", "success_rate", "throughput_req_s", "p50_ms", "p95_ms", "max_ms",
    "reason_breakdown", "knee", "gap_after_s", "notes",
]


@dataclass
class BunchStat:
    bunch_id: int
    ts_utc: str
    target: str
    kind: str
    concurrency: int
    n_req: int
    n_ok: int
    n_fail: int
    success_rate: float
    throughput_req_s: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    reason_breakdown: dict = field(default_factory=dict)
    knee: bool = False
    gap_after_s: float = 0.0
    notes: str = ""

    def row(self) -> list:
        return [
            self.bunch_id, self.ts_utc, self.target, self.kind, self.concurrency,
            self.n_req, self.n_ok, self.n_fail, self.success_rate,
            self.throughput_req_s, self.p50_ms, self.p95_ms, self.max_ms,
            json.dumps(self.reason_breakdown), self.knee, self.gap_after_s, self.notes,
        ]


def bunch_stats_from(records: list[RequestRecord], *, bunch_id, target, kind,
                     concurrency, wall_s) -> BunchStat:
    lat = [r.latency_ms for r in records if r.latency_ms is not None]
    n = len(records)
    n_ok = sum(1 for r in records if r.outcome == "success")
    reasons: dict = {}
    for r in records:
        reasons[r.reason_category] = reasons.get(r.reason_category, 0) + 1
    p50 = round(statistics.median(lat), 1) if lat else 0.0
    p95 = round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)], 1) if len(lat) >= 2 else (lat[0] if lat else 0.0)
    return BunchStat(
        bunch_id=bunch_id, ts_utc=utcnow_iso(), target=target, kind=kind,
        concurrency=concurrency, n_req=n, n_ok=n_ok, n_fail=n - n_ok,
        success_rate=round(n_ok / n, 3) if n else 0.0,
        throughput_req_s=round(n / wall_s, 2) if wall_s > 0 else 0.0,
        p50_ms=p50, p95_ms=p95, max_ms=round(max(lat), 1) if lat else 0.0,
        reason_breakdown=reasons,
    )


class StressLog:
    def __init__(self, run_id: str, logs_root: str):
        self.run_id = run_id
        self.dir = os.path.join(logs_root, run_id)
        os.makedirs(self.dir, exist_ok=True)
        self.requests_csv = os.path.join(self.dir, "requests.csv")
        self.bunches_csv = os.path.join(self.dir, "bunches.csv")
        self.events_log = os.path.join(self.dir, "events.log")
        self.checkpoint_json = os.path.join(self.dir, "checkpoint.json")

    @staticmethod
    def _append(path, columns, rows):
        new = not (os.path.exists(path) and os.path.getsize(path) > 0)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(columns)
            for row in rows:
                w.writerow(row)

    def record_requests(self, records: list[RequestRecord]):
        if records:
            self._append(self.requests_csv, REQUEST_COLUMNS,
                         [[getattr(r, c) for c in REQUEST_COLUMNS] for r in records])

    def write_bunch(self, b: BunchStat):
        self._append(self.bunches_csv, BUNCH_COLUMNS, [b.row()])

    def event(self, msg: str):
        line = f"{utcnow_iso()}  {msg}"
        with open(self.events_log, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print("  " + line)

    def checkpoint(self, state: dict):
        with open(self.checkpoint_json, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def write_summary(self, summary: dict):
        with open(os.path.join(self.dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        md = ["# Residual harness summary — " + self.run_id, ""]
        md.append(f"- bunches: {summary.get('bunches')}  requests: {summary.get('requests')}")
        md.append(f"- elapsed: {summary.get('elapsed_seconds')} s   aborted: {summary.get('aborted')}")
        md.append("")
        md.append("## Recommended safe-max concurrency (below the knee) per target")
        for t, v in (summary.get("safe_max") or {}).items():
            md.append(f"- **{t}**: {v}")
        md.append("")
        md.append("## Failure-reason catalogue")
        for r, c in (summary.get("reason_totals") or {}).items():
            md.append(f"- {r}: {c}")
        with open(os.path.join(self.dir, "summary.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
