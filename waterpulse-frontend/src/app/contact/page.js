import Footer from "@/components/Footer";

export const metadata = {
  title: "Contact — WaterPulse Canada",
  description: "Get in touch with WaterPulse — feedback, bug reports, and contributions are welcome.",
};

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <main className="flex-1 pt-24 pb-16 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="font-display text-4xl sm:text-5xl mb-3">Get in touch</h1>
          <p className="text-lg text-slate-600 mb-12">
            WaterPulse is built and maintained as a personal project. Feedback,
            bug reports, and ideas for new features are all welcome.
          </p>

          <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8 space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-2">
                Reporting a data issue
              </h2>
              <p className="text-slate-700 leading-relaxed">
                If a station is showing wrong or stale readings, the source data
                most often comes from{" "}
                <a
                  href="https://wateroffice.ec.gc.ca/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1e6ba8] hover:underline"
                >
                  ECCC&rsquo;s Water Office
                </a>{" "}
                or{" "}
                <a
                  href="https://rivers.alberta.ca/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1e6ba8] hover:underline"
                >
                  Rivers Alberta
                </a>
                . If those sources show the same number, the sensor itself is
                the issue and we mirror what the network publishes. Drop us a
                note anyway &mdash; it helps us spot stations that need
                attention.
              </p>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-2">
                Response time
              </h2>
              <p className="text-slate-700 leading-relaxed">
                This is a side project, not a 24/7 service. We try to read every
                message but a reply may take a few days.
              </p>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
