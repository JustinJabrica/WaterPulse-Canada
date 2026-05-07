import Link from "next/link";
import Footer from "@/components/Footer";

export const metadata = {
  title: "About — WaterPulse Canada",
  description:
    "WaterPulse Canada surfaces real-time river, lake, and reservoir conditions from official Canadian monitoring networks for recreational and professional users.",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <main className="flex-1 pt-24 pb-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-display text-4xl sm:text-5xl mb-3">About WaterPulse</h1>
          <p className="text-lg text-slate-600 mb-12">
            Real-time river, lake, and reservoir conditions for everyone who spends
            time on Canada&rsquo;s water.
          </p>

          <section className="space-y-4 mb-12">
            <h2 className="font-display text-2xl">What it is</h2>
            <p className="text-slate-700 leading-relaxed">
              WaterPulse pulls live readings from official Canadian hydrometric
              networks and presents them in one place: water level, flow rate,
              reservoir capacity, weather, and air quality for thousands of
              monitored stations across the country. Conditions are rated against
              historical norms so a single glance tells you whether a river is
              running unusually high, low, or about average for this time of year.
            </p>
          </section>

          <section className="space-y-4 mb-12">
            <h2 className="font-display text-2xl">Who it&rsquo;s for</h2>
            <p className="text-slate-700 leading-relaxed">
              Anglers planning a weekend, paddlers checking flows before a trip,
              swimmers and rafters scouting conditions, and the professionals
              whose work depends on accurate water data &mdash; fire services,
              river rescue, field crews, and municipal staff.
            </p>
          </section>

          <section className="space-y-4 mb-12">
            <h2 className="font-display text-2xl">Where the data comes from</h2>
            <ul className="space-y-3 text-slate-700 leading-relaxed">
              <li>
                <strong className="text-slate-900">
                  Environment and Climate Change Canada (ECCC)
                </strong>{" "}
                &mdash; the primary source for all of Canada, covering roughly
                2,700 active hydrometric stations.
              </li>
              <li>
                <strong className="text-slate-900">Government of Alberta</strong>{" "}
                &mdash; supplementary provincial readings that enrich shared
                stations and add provincial-only sites that ECCC doesn&rsquo;t
                cover.
              </li>
              <li>
                <strong className="text-slate-900">Open-Meteo</strong> &mdash;
                weather, humidity, sunrise/sunset, and air-quality forecasts for
                each station&rsquo;s coordinates.
              </li>
            </ul>
            <p className="text-slate-700 leading-relaxed">
              Readings refresh every ten minutes. Historical norms are computed
              against up to five years of daily means in a &plusmn;7 day window.
            </p>
          </section>

          <section className="space-y-4 mb-12">
            <h2 className="font-display text-2xl">Important caveat</h2>
            <p className="text-slate-700 leading-relaxed">
              All water data shown on WaterPulse is{" "}
              <strong className="text-slate-900">provisional</strong>. It comes
              directly from automated sensors and has not been reviewed for
              accuracy. Use it as one input alongside your own judgement, local
              knowledge, and official advisories &mdash; not as a sole basis for
              safety decisions.
            </p>
          </section>

          <div className="mt-16 flex flex-wrap gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-[#2196f3] hover:bg-[#1e6ba8] transition-colors"
            >
              Browse stations
            </Link>
            <Link
              href="/map"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 transition-colors"
            >
              Open the map
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
