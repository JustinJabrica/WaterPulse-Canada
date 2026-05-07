import Link from "next/link";
import Footer from "@/components/Footer";

export const metadata = {
  title: "Advanced Data — WaterPulse Canada",
  description:
    "Long-range historical viewer, station-level statistics, and bulk data export for WaterPulse — coming soon.",
};

export default function AdvancedDataPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <main className="flex-1 pt-24 pb-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block text-xs font-semibold tracking-wider uppercase text-[#1e6ba8] bg-[#e3f2fd] px-3 py-1 rounded-full mb-4">
            Coming soon
          </span>
          <h1 className="font-display text-4xl sm:text-5xl mb-3">Advanced Data</h1>
          <p className="text-lg text-slate-600 mb-12">
            Long-range historical analysis for any monitored station &mdash; not
            yet built, but here&rsquo;s what&rsquo;s on the way.
          </p>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="font-display text-xl mb-2">Historical viewer</h2>
              <p className="text-slate-700 leading-relaxed">
                Multi-year flow and level charts for individual stations, with
                overlays for daily means, percentile bands, and year-over-year
                comparisons. Useful for spotting drought trends, melt timing,
                and unusual events.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="font-display text-xl mb-2">Station statistics</h2>
              <p className="text-slate-700 leading-relaxed">
                Long-term means, variability, and percentile breakdowns by
                month and season. Quick way to answer &ldquo;is this normal for
                this time of year?&rdquo; without scrolling through chart data.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="font-display text-xl mb-2">Data export</h2>
              <p className="text-slate-700 leading-relaxed">
                CSV and JSON downloads for any station and date range, so you
                can pull WaterPulse data into your own analyses, notebooks, or
                dashboards. Will respect the same provisional-data caveat as
                the rest of the site.
              </p>
            </div>
          </div>

          <p className="text-sm text-slate-500 mt-10">
            In the meantime, real-time conditions and ratings are available
            through the{" "}
            <Link href="/dashboard" className="text-[#1e6ba8] hover:underline">
              dashboard
            </Link>{" "}
            and the{" "}
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
