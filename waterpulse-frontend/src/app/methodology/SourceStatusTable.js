"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import {
  SOURCES,
  STATUS_META,
  surfaceFor,
  groupByGeography,
  withRefNumbers,
} from "@/lib/sourceRegistry";

const NUMBERED = withRefNumbers(SOURCES);
const REF_NUMBER = Object.fromEntries(NUMBERED.map((s) => [s.id, s.ref]));
const GEO = groupByGeography(SOURCES);

// Live-health → dot appearance. Falls back to lifecycle status when the backend
// has no health entry for a source (e.g. "possible" sources never probed).
const HEALTH_DOT = {
  up: { color: "#10b981", pulse: true, label: "Live" },
  degraded: { color: "#f59e0b", pulse: false, label: "Degraded / stale" },
  gated: { color: "#f59e0b", pulse: false, label: "Reachable (key required)" },
  down: { color: "#ef4444", pulse: false, label: "Unreachable" },
};

function dotFor(source, live) {
  const h = live?.health;
  if (h && HEALTH_DOT[h]) return HEALTH_DOT[h];
  // fallback to lifecycle status (implemented pulses, else static)
  const meta = STATUS_META[source.status] || STATUS_META.possible;
  return { color: meta.dot, pulse: source.status === "implemented", label: meta.label };
}

function Dot({ source, live }) {
  const d = dotFor(source, live);
  const ageTxt =
    live?.data_age_minutes != null
      ? ` · updated ${Math.round(live.data_age_minutes)} min ago`
      : "";
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${d.pulse ? "animate-pulse" : ""}`}
      style={{ backgroundColor: d.color }}
      title={`${d.label}${ageTxt}${live?.basis ? ` (${live.basis})` : ""}`}
      aria-label={d.label}
    />
  );
}

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.possible;
  const cls = {
    implemented: "bg-emerald-50 text-emerald-700 border-emerald-200",
    testing: "bg-amber-50 text-amber-700 border-amber-200",
    possible: "bg-slate-100 text-slate-500 border-slate-200",
  }[status];
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${cls} whitespace-nowrap`}>
      {meta.label}
    </span>
  );
}

function Row({ s, live }) {
  return (
    <li className="flex items-start gap-2 py-2 border-b border-slate-100 last:border-0">
      <span className="mt-1.5">
        <Dot source={s} live={live} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm font-medium text-slate-900">{s.name}</span>
          <StatusBadge status={s.status} />
          <span className="text-[11px] text-slate-400">
            {surfaceFor(s) === "ad-supported" ? "commercial-OK" : "ad-free only"}
          </span>
          <a href={`#ref-${REF_NUMBER[s.id]}`} className="text-[11px] text-[#1e6ba8] hover:underline">
            [{REF_NUMBER[s.id]}]
          </a>
        </div>
        <div className="text-xs text-slate-500">{s.operator}</div>
        <div className="mt-0.5 flex flex-wrap gap-1">
          {s.categories.map((c) => (
            <span key={c} className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {c}
            </span>
          ))}
        </div>
        {s.depth && <div className="text-[11px] text-slate-400 mt-0.5">Available depth: {s.depth}</div>}
        {s.note && <div className="text-[11px] text-slate-400 mt-0.5 italic">{s.note}</div>}
      </div>
    </li>
  );
}

function Group({ title, sources, status }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mb-5">
      <h4 className="text-xs font-semibold tracking-wider uppercase text-slate-500 mb-1">{title}</h4>
      <ul>
        {sources.map((s) => (
          <Row key={s.id} s={s} live={status[s.id]} />
        ))}
      </ul>
    </div>
  );
}

export default function SourceStatusTable() {
  const [status, setStatus] = useState({});
  const [stamp, setStamp] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .get("/api/sources/status")
        .then((data) => {
          if (cancelled) return;
          setStatus(data?.sources || {});
          setStamp(data?.generated_at || null);
        })
        .catch(() => {}); // on failure, dots fall back to lifecycle status
    load();
    const t = setInterval(load, 60000); // poll every 60s
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const counts = SOURCES.reduce((a, s) => ((a[s.status] = (a[s.status] || 0) + 1), a), {});

  return (
    <div>
      {/* status legend */}
      <div className="flex flex-wrap gap-4 mb-6 text-xs">
        {Object.entries(STATUS_META).map(([key, m]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${key === "implemented" ? "animate-pulse" : ""}`}
              style={{ backgroundColor: m.dot }}
            />
            <span className="text-slate-700 font-medium">{m.label}</span>
            <span className="text-slate-400">({counts[key] || 0})</span>
          </span>
        ))}
        <span className="text-slate-400">
          {stamp ? "● live health" : "○ live health unavailable — showing lifecycle status"}
        </span>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <Group title="National / Canada-wide" sources={GEO.national} status={status} />
        {GEO.provinces.map((p) => (
          <div key={p.code} className="mb-5">
            <h3 className="font-display text-lg text-slate-900 mb-2 pt-2 border-t border-slate-100">
              {p.name}
            </h3>
            <Group title="Provincial / territorial" sources={p.provincial} status={status} />
            {Object.entries(p.cities).map(([city, list]) => (
              <Group key={city} title={city} sources={list} status={status} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
