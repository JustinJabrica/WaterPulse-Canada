import Link from "next/link";
import Footer from "@/components/Footer";
import {
  SOURCES,
  STATUS_META,
  surfaceFor,
  groupByGeography,
  withRefNumbers,
} from "@/lib/sourceRegistry";
import { SECTIONS } from "@/lib/methodologyContent";

export const metadata = {
  title: "Data & Methodology — WaterPulse Canada",
  description:
    "Living documentation of every data source WaterPulse uses or is testing, and exactly how each condition, rating, prediction, and recommendation is calculated — and how reliable it is.",
};

// Stable IEEE reference numbering (registry order) + id→number lookup.
const NUMBERED = withRefNumbers(SOURCES);
const REF_NUMBER = Object.fromEntries(NUMBERED.map((s) => [s.id, s.ref]));

/* ── Small presentational helpers (server-rendered) ───────────────── */

function StatusDot({ status }) {
  const meta = STATUS_META[status] || STATUS_META.possible;
  // Implemented sources are live → the dot pulses; others are static.
  const pulse = status === "implemented" ? "animate-pulse" : "";
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${pulse}`}
      style={{ backgroundColor: meta.dot }}
      title={`${meta.label} — ${meta.blurb}`}
      aria-label={meta.label}
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

function SourceRow({ s }) {
  return (
    <li className="flex items-start gap-2 py-2 border-b border-slate-100 last:border-0">
      <span className="mt-1.5">
        <StatusDot status={s.status} />
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

function SourceGroup({ title, sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mb-5">
      <h4 className="text-xs font-semibold tracking-wider uppercase text-slate-500 mb-1">{title}</h4>
      <ul>
        {sources.map((s) => (
          <SourceRow key={s.id} s={s} />
        ))}
      </ul>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────── */

export default function MethodologyPage() {
  const geo = groupByGeography(SOURCES);
  const counts = SOURCES.reduce((acc, s) => ((acc[s.status] = (acc[s.status] || 0) + 1), acc), {});

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <main className="flex-1 pt-24 pb-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block text-xs font-semibold tracking-wider uppercase text-[#1e6ba8] bg-[#e3f2fd] px-3 py-1 rounded-full mb-4">
            Living documentation
          </span>
          <h1 className="font-display text-4xl sm:text-5xl mb-3">Data &amp; Methodology</h1>
          <p className="text-lg text-slate-600 mb-6">
            Where every number on WaterPulse comes from, how each condition, rating, prediction, and
            recommendation is calculated, and how much to trust it. This page is kept up to date as
            sources move from <em>possible</em> to <em>research &amp; testing</em> to{" "}
            <em>implemented</em>.
          </p>

          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 mb-12">
            <strong className="text-slate-900">A note on honesty.</strong> We only label a source{" "}
            <em>Implemented</em> if it is genuinely live and serving data in the app today. Water data is
            often <em>provisional</em> (subject to revision), and some values are <em>modeled estimates</em>,
            not direct measurements. We try to say which is which — see{" "}
            <a href="#reliability" className="text-[#1e6ba8] hover:underline">
              how reliable is it
            </a>
            . WaterPulse is not an emergency service; see{" "}
            <a href="#safety" className="text-[#1e6ba8] hover:underline">
              safety &amp; limitations
            </a>
            .
          </div>

          {/* ── Section 1: source catalog ── */}
          <section id="sources" className="scroll-mt-24 mb-14">
            <h2 className="font-display text-2xl mb-2">Where our data comes from</h2>
            <p className="text-slate-600 mb-4">
              The full landscape of sources, organized by geography. Each is flagged by status, with a
              live indicator, its licence surface, and an IEEE reference.
            </p>

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
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <SourceGroup title="National / Canada-wide" sources={geo.national} />
              {geo.provinces.map((p) => (
                <div key={p.code} className="mb-5">
                  <h3 className="font-display text-lg text-slate-900 mb-2 pt-2 border-t border-slate-100">
                    {p.name}
                  </h3>
                  <SourceGroup title="Provincial / territorial" sources={p.provincial} />
                  {Object.entries(p.cities).map(([city, list]) => (
                    <SourceGroup key={city} title={city} sources={list} />
                  ))}
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-3">
              Live indicator: a pulsing green dot marks a source that is implemented and serving data now;
              amber marks sources under research &amp; testing; grey marks identified-but-untested
              candidates. Real-time per-source health is being wired up.
            </p>
          </section>

          {/* ── Sections 2–7: methodology prose (layered) ── */}
          {SECTIONS.map((sec) => (
            <section key={sec.id} id={sec.id} className="scroll-mt-24 mb-12">
              <h2 className="font-display text-2xl mb-2">{sec.title}</h2>
              <p className="text-slate-700 leading-relaxed mb-3">{sec.summary}</p>
              <details className="rounded-xl border border-slate-200 bg-white p-0 group">
                <summary className="cursor-pointer select-none px-5 py-3 text-sm font-medium text-[#1e6ba8] hover:bg-slate-50 rounded-xl">
                  How it&rsquo;s calculated / how reliable
                </summary>
                <div className="px-5 pb-5 pt-1 space-y-4 border-t border-slate-100">
                  {sec.detail.map((block, i) => (
                    <div key={i}>
                      {block.h && <h3 className="font-semibold text-slate-900 text-sm mb-1">{block.h}</h3>}
                      {block.body && <p className="text-slate-700 text-sm leading-relaxed">{block.body}</p>}
                      {block.bullets && (
                        <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
                          {block.bullets.map((b, j) => (
                            <li key={j}>{b}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                  {sec.refs && sec.refs.length > 0 && (
                    <p className="text-xs text-slate-400 pt-1">
                      Sources:{" "}
                      {sec.refs
                        .filter((id) => REF_NUMBER[id])
                        .map((id, i) => (
                          <span key={id}>
                            {i > 0 && ", "}
                            <a href={`#ref-${REF_NUMBER[id]}`} className="text-[#1e6ba8] hover:underline">
                              [{REF_NUMBER[id]}]
                            </a>
                          </span>
                        ))}
                    </p>
                  )}
                </div>
              </details>
            </section>
          ))}

          {/* ── Section 8: IEEE references ── */}
          <section id="references" className="scroll-mt-24">
            <h2 className="font-display text-2xl mb-2">Sources &amp; attribution</h2>
            <p className="text-slate-600 mb-4 text-sm">
              Full attribution for every source above, in IEEE format. WaterPulse displays these per
              each provider&rsquo;s open-data licence.
            </p>
            <ol className="space-y-2 text-xs text-slate-600 leading-relaxed">
              {NUMBERED.map((s) => (
                <li key={s.id} id={`ref-${s.ref}`} className="scroll-mt-24 flex gap-2">
                  <span className="text-slate-400 shrink-0">[{s.ref}]</span>
                  <span>
                    {s.citation}{" "}
                    <span className="text-slate-400">({STATUS_META[s.status].label}; {s.licence})</span>
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <p className="text-sm text-slate-500 mt-12">
            See live conditions on the{" "}
            <Link href="/dashboard" className="text-[#1e6ba8] hover:underline">
              dashboard
            </Link>{" "}
            and{" "}
            <Link href="/map" className="text-[#1e6ba8] hover:underline">
              map
            </Link>
            .
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
