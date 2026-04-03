"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import RatingPill from "@/components/RatingPill";
import api from "@/lib/api";

/* ─────────────────────────────────────────────
   WaterPulse Canada — Landing Page
   ───────────────────────────────────────────── */


// ── Inline SVG icons ─────────────────────────

const IconDroplet = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z" />
  </svg>
);

const IconThermometer = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 14.76V3.5a2.5 2.5 0 00-5 0v11.26a4.5 4.5 0 105 0z" />
  </svg>
);

const IconMap = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
    <line x1="8" y1="2" x2="8" y2="18" />
    <line x1="16" y1="6" x2="16" y2="22" />
  </svg>
);

const IconStar = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);

const IconClock = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconShield = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const IconWind = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.7 7.7A2.5 2.5 0 0119 12H2" />
    <path d="M9.6 4.6A2 2 0 0111 8H2" />
    <path d="M12.6 19.4A2 2 0 0014 16H2" />
  </svg>
);

const IconFish = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6.5 12c3-6 10-6 14-2-4 4-11 4-14-2z" />
    <path d="M6.5 12c-3-2-4-5-4.5-6 2 .5 4 1.5 4.5 6z" />
    <circle cx="16" cy="11.5" r="0.5" fill="currentColor" />
  </svg>
);

const IconHardHat = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 18h20" />
    <path d="M4 18v-2a8 8 0 0116 0v2" />
    <path d="M12 6V2" />
    <path d="M8 18v-6" />
    <path d="M16 18v-6" />
  </svg>
);

const IconBarChart = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

const IconArrowRight = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" />
    <polyline points="12 5 19 12 12 19" />
  </svg>
);

const IconChevronDown = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconWave = ({ className = "w-6 h-6" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12c1.5-2 3.5-3 5.5-1s4 1 5.5-1 3.5-3 5.5-1 3.5 3 5.5 1" />
    <path d="M2 17c1.5-2 3.5-3 5.5-1s4 1 5.5-1 3.5-3 5.5-1 3.5 3 5.5 1" opacity="0.5" />
  </svg>
);


// ── Water ripple background ──────────────────

function WaterRipple() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full border opacity-[0.06]"
          style={{
            width: `${300 + i * 200}px`,
            height: `${300 + i * 200}px`,
            left: "50%",
            top: "60%",
            transform: "translate(-50%, -50%)",
            borderColor: "#64b5f6",
            animation: `ripple ${6 + i * 2}s ease-in-out infinite`,
            animationDelay: `${i * 1.5}s`,
          }}
        />
      ))}
    </div>
  );
}


// ── Animated counter ─────────────────────────

function AnimatedCounter({ target, suffix = "", duration = 2000 }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const start = performance.now();
          const step = (now) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * target));
            if (progress < 1) requestAnimationFrame(step);
          };
          requestAnimationFrame(step);
        }
      },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target, duration]);

  return (
    <span ref={ref}>
      {count.toLocaleString()}
      {suffix}
    </span>
  );
}


// ── Fade-in on scroll ────────────────────────

function FadeIn({ children, className = "", delay = 0 }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}


// ── Feature card ─────────────────────────────

function FeatureCard({ icon, title, description, delay = 0 }) {
  return (
    <FadeIn delay={delay}>
      <div className="group relative rounded-2xl p-6 transition-all duration-300 bg-white/60 backdrop-blur-sm border border-slate-200/80 hover:bg-white hover:shadow-lg hover:border-[#2196f3]/30 hover:shadow-blue-900/5">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-all duration-300 bg-gradient-to-br from-blue-50 to-sky-50 border border-blue-200/60 text-[#1e6ba8] group-hover:scale-110 group-hover:from-blue-100 group-hover:to-sky-100">
          {icon}
        </div>
        <h3 className="font-semibold text-slate-900 text-[1.05rem] mb-2 tracking-tight">{title}</h3>
        <p className="text-slate-600 text-sm leading-relaxed">{description}</p>
      </div>
    </FadeIn>
  );
}


// ── Audience card ────────────────────────────

function AudienceCard({ icon, title, people, description, accent, delay = 0 }) {
  return (
    <FadeIn delay={delay}>
      <div className={`relative overflow-hidden rounded-2xl border p-8 transition-all duration-300 hover:shadow-xl hover:shadow-slate-900/5 hover:-translate-y-1 ${accent}`}>
        <div className="absolute top-0 right-0 w-40 h-40 opacity-[0.04] pointer-events-none">
          {icon && typeof icon === "object" ? (
            <div className="w-full h-full">{icon}</div>
          ) : null}
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-white/80 border border-white flex items-center justify-center text-slate-700">
              {icon}
            </div>
            <h3 className="font-bold text-slate-900 text-lg tracking-tight">{title}</h3>
          </div>
          <p className="text-slate-700 text-sm leading-relaxed mb-5">{description}</p>
          <div className="flex flex-wrap gap-2">
            {people.map((p) => (
              <span
                key={p}
                className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-white/70 text-slate-700 border border-slate-200/60"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      </div>
    </FadeIn>
  );
}




// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  MAIN PAGE COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function LandingPage() {
  const [stationStats, setStationStats] = useState({
    total: null,
    active: null,
    basins: null,
  });

  // ── Fetch live station count from backend ──
  useEffect(() => {
    async function fetchStatus() {
      try {
        const data = await api.get("/api/admin/status");

        const total = data.stations?.total ?? null;
        const active = data.current_readings?.total ?? null;
        const provinceCount = data.stations?.by_province
          ? Object.keys(data.stations.by_province).filter((k) => k !== "None").length
          : null;

        setStationStats({ total, active, provinces: provinceCount });
      } catch (err) {
        console.error("Failed to fetch station stats:", err);
        setStationStats({ total: null, active: null, provinces: null });
      }
    }
    fetchStatus();
  }, []);

  const heroStationCount = stationStats.active ?? stationStats.total;
  const heroStationLabel = stationStats.active
    ? "active stations across Canada right now"
    : "monitoring stations across Canada";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 overflow-x-hidden">

      {/* ━━━━━━━━━━━━━━━━ NAV ━━━━━━━━━━━━━━━━ */}
      <Navbar transparent />

      {/* ━━━━━━━━━━━━━━━━ HERO ━━━━━━━━━━━━━━━━ */}
      <header className="relative min-h-[92vh] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0d2137] via-[#12304d] to-[#0f2a44]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
          }}
        />
        <WaterRipple />
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#2196f3]/40 to-transparent" />

        <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.07] border border-white/[0.1] text-[#90caf9] text-sm font-medium mb-8 animate-fade-up backdrop-blur-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            {heroStationCount
              ? <>Live data from {heroStationCount.toLocaleString()} {heroStationLabel}</>
              : "Live water data across Canada"
            }
          </div>

          <h1 className="font-display text-5xl sm:text-6xl md:text-7xl text-white leading-[1.08] mb-6 animate-fade-up animate-fade-up-delay-1">
            Know your river
            <br />
            <span className="bg-gradient-to-r from-[#64b5f6] via-[#42a5f5] to-[#90caf9] bg-clip-text text-transparent">
              before you go.
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed mb-10 animate-fade-up animate-fade-up-delay-2">
            Real-time water levels, flow rates, weather, and air quality for
            rivers, lakes, and reservoirs across Canada — live-updating every
            five minutes while you&rsquo;re watching.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 animate-fade-up animate-fade-up-delay-3">
            <Link href="/register" className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-sm font-bold text-white transition-all duration-200 shadow-lg bg-[#2196f3] hover:bg-[#42a5f5] shadow-blue-900/30 hover:shadow-[#2196f3]/30">
              Create Free Account
              <IconArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link href="/dashboard" className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-sm font-semibold bg-white/10 text-white border border-white/15 hover:bg-white/15 backdrop-blur-sm transition-all duration-200">
              Explore as Guest
            </Link>
          </div>

          <div className="mt-16 flex flex-col items-center gap-1 text-slate-500 animate-fade-up" style={{ animationDelay: "1s" }}>
            <span className="text-xs tracking-wider uppercase">Learn more</span>
            <IconChevronDown className="w-5 h-5 animate-bounce" />
          </div>
        </div>
      </header>

      {/* ━━━━━━━━━━━━━━━━ STATS BAR ━━━━━━━━━━━━━━━━ */}
      <section className="relative -mt-8 z-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="bg-white rounded-2xl shadow-xl shadow-slate-900/5 border border-slate-200/80 p-6 sm:p-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 text-center">
              <div>
                <div className="font-display text-3xl sm:text-4xl text-[#1e6ba8] mb-1">
                  {stationStats.active != null || stationStats.total != null
                    ? <AnimatedCounter target={stationStats.active ?? stationStats.total} />
                    : <span className="text-slate-300">&mdash;</span>
                  }
                </div>
                <div className="text-sm text-slate-500 font-medium">Live Stations</div>
              </div>
              <div>
                <div className="font-display text-3xl sm:text-4xl text-[#1e6ba8] mb-1">
                  {stationStats.provinces != null
                    ? <AnimatedCounter target={stationStats.provinces} />
                    : <span className="text-slate-300">&mdash;</span>
                  }
                </div>
                <div className="text-sm text-slate-500 font-medium">Provinces &amp; Territories</div>
              </div>
              <div>
                <div className="font-display text-3xl sm:text-4xl text-[#1e6ba8] mb-1">
                  &le; <AnimatedCounter target={10} suffix=" min" />
                </div>
                <div className="text-sm text-slate-500 font-medium">Refresh Cycle</div>
              </div>
              <div>
                <div className="font-display text-3xl sm:text-4xl text-[#1e6ba8] mb-1">
                  <AnimatedCounter target={7} suffix=" day" />
                </div>
                <div className="text-sm text-slate-500 font-medium">Weather Forecast</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ WHAT IS WATERPULSE ━━━━━━━━━━━━━━━━ */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <FadeIn>
            <span className="inline-block text-xs font-bold tracking-[0.2em] uppercase text-[#1e6ba8] mb-4">
              What is WaterPulse?
            </span>
          </FadeIn>
          <FadeIn delay={100}>
            <h2 className="font-display text-3xl sm:text-4xl text-slate-900 mb-6 leading-tight">
              Canada&rsquo;s water conditions,
              <br className="hidden sm:block" />
              made simple and accessible.
            </h2>
          </FadeIn>
          <FadeIn delay={200}>
            <p className="text-slate-600 text-lg leading-relaxed max-w-3xl mx-auto mb-6">
              WaterPulse collects real-time data from federal and provincial monitoring
              networks across all 13 provinces and territories and combines it with weather
              forecasts and air quality readings. Instead of parsing raw data tables, you get
              clear condition ratings — <em>Very Low</em> through <em>Very High</em> — that
              tell you at a glance whether conditions are normal for the time of year.
            </p>
          </FadeIn>
          <FadeIn delay={300}>
            <div className="flex flex-wrap items-center justify-center gap-2">
              <RatingPill rating="very low" />
              <RatingPill rating="low" />
              <RatingPill rating="average" />
              <RatingPill rating="high" />
              <RatingPill rating="very high" />
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ WHO IT'S FOR ━━━━━━━━━━━━━━━━ */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <span className="inline-block text-xs font-bold tracking-[0.2em] uppercase text-[#1e6ba8] mb-4">
              Who it&rsquo;s for
            </span>
          </FadeIn>
          <FadeIn delay={100}>
            <h2 className="font-display text-3xl sm:text-4xl text-slate-900 mb-12 leading-tight">
              Built for everyone who depends
              <br className="hidden sm:block" />
              on Canada&rsquo;s waterways.
            </h2>
          </FadeIn>

          <div className="grid md:grid-cols-2 gap-6">
            <AudienceCard
              icon={<IconFish />}
              title="Recreational Users"
              description="Plan your next trip with confidence. Check conditions before driving to the river — know whether levels are safe for wading, paddling is possible, or flow is too high for your activity."
              people={["Anglers", "Kayakers", "Canoeists", "Paddle Boarders", "Rafters", "Swimmers", "Campers"]}
              accent="bg-gradient-to-br from-blue-50/80 to-sky-50/60 border-blue-200/50"
              delay={0}
            />
            <AudienceCard
              icon={<IconHardHat />}
              title="Professionals & Public Service"
              description="Access the same station data used by government agencies, formatted for quick situational awareness. Monitor conditions across basins, track rising levels, and share data with your team."
              people={["Fire Services", "River Rescue", "Field Workers", "Data Analysts", "Municipal Staff", "Educators"]}
              accent="bg-gradient-to-br from-amber-50/80 to-orange-50/60 border-amber-200/50"
              delay={150}
            />
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ WAVE DIVIDER ━━━━━━━━━━━━━━━━ */}
      <div className="wave-divider h-px w-full" />

      {/* ━━━━━━━━━━━━━━━━ FEATURES ━━━━━━━━━━━━━━━━ */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeIn>
            <span className="inline-block text-xs font-bold tracking-[0.2em] uppercase text-[#1e6ba8] mb-4">
              Features
            </span>
          </FadeIn>
          <FadeIn delay={100}>
            <h2 className="font-display text-3xl sm:text-4xl text-slate-900 mb-4 leading-tight">
              Everything you need, nothing you don&rsquo;t.
            </h2>
          </FadeIn>
          <FadeIn delay={200}>
            <p className="text-slate-500 text-lg mb-12 max-w-2xl">
              Designed around the decisions you actually make when heading to the water.
            </p>
          </FadeIn>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon={<IconDroplet className="w-5 h-5" />}
              title="Flow & Level Ratings"
              description="Current water levels and flow rates rated against historical norms. See at a glance if conditions are unusually high, low, or within the typical range for the season."
              delay={0}
            />
            <FeatureCard
              icon={<IconThermometer className="w-5 h-5" />}
              title="Weather & Air Quality"
              description="Temperature, wind, UV index, visibility, and AQI for every station location. Especially critical during wildfire smoke season."
              delay={80}
            />
            <FeatureCard
              icon={<IconMap className="w-5 h-5" />}
              title="Interactive Map"
              description="Browse all stations on a Leaflet-powered map. Tap any station to see conditions, add it to your favourites, or explore nearby sites."
              delay={160}
            />
            <FeatureCard
              icon={<IconStar className="w-5 h-5" />}
              title="Favourites & Folders"
              description="Save the stations you care about. Organize them into folders and share collections with friends, your fishing club, or your work team."
              delay={240}
            />
            <FeatureCard
              icon={<IconBarChart className="w-5 h-5" />}
              title="Historical Data"
              description="Browse daily averages and 'On This Day' comparisons. View how current conditions compare to previous years with detailed graphs and explanations."
              delay={320}
            />
            <FeatureCard
              icon={<IconClock className="w-5 h-5" />}
              title="10-Minute Updates"
              description="Data refreshes automatically every ten minutes around the clock. Every reading includes a timestamp so you always know how fresh the data is."
              delay={400}
            />
          </div>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ DATA TRUST ━━━━━━━━━━━━━━━━ */}
      <section className="py-24 px-6 bg-gradient-to-b from-slate-50 to-slate-100/80">
        <div className="max-w-4xl mx-auto text-center">
          <FadeIn>
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl border mb-6 bg-blue-50 border-blue-200/60 text-[#1e6ba8]">
              <IconShield className="w-7 h-7" />
            </div>
          </FadeIn>
          <FadeIn delay={100}>
            <h2 className="font-display text-3xl sm:text-4xl text-slate-900 mb-6 leading-tight">
              Trusted public data.
              <br className="hidden sm:block" />
              Open source technology.
            </h2>
          </FadeIn>
          <FadeIn delay={200}>
            <p className="text-slate-600 text-lg leading-relaxed max-w-3xl mx-auto mb-10">
              Water data is sourced from Environment and Climate Change Canada&rsquo;s
              national hydrometric network and provincial monitoring systems like
              Alberta&rsquo;s River Basins. Weather and air quality come from Open-Meteo,
              a free and open-source weather API. WaterPulse does not generate or alter any
              readings — it organizes and presents them clearly so you can make informed decisions.
            </p>
          </FadeIn>
          <FadeIn delay={300}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-slate-500">
              <div className="flex items-center gap-2">
                <IconWave className="w-4 h-4 text-[#2196f3]" />
                <span>api.weather.gc.ca</span>
              </div>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-slate-300" />
              <div className="flex items-center gap-2">
                <IconWave className="w-4 h-4 text-[#2196f3]" />
                <span>rivers.alberta.ca</span>
              </div>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-slate-300" />
              <div className="flex items-center gap-2">
                <IconWind className="w-4 h-4 text-[#2196f3]" />
                <span>Open-Meteo Weather API</span>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ GUEST CALLOUT ━━━━━━━━━━━━━━━━ */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <FadeIn>
            <div className="relative rounded-2xl border border-slate-200/80 bg-white p-8 sm:p-12 overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-blue-50 to-transparent rounded-bl-full pointer-events-none" />
              <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-6">
                <div className="flex-1">
                  <h3 className="font-display text-2xl text-slate-900 mb-2">
                    No account needed to get started.
                  </h3>
                  <p className="text-slate-600 leading-relaxed">
                    Browse all stations, view conditions, and explore the map as a guest.
                    Create an account when you&rsquo;re ready to save favourites and build
                    personalized collections.
                  </p>
                </div>
                <Link href="/dashboard" className="group shrink-0 inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold bg-slate-900 text-white hover:bg-slate-800 transition-colors duration-200 shadow-sm">
                  Explore as Guest
                  <IconArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ FINAL CTA ━━━━━━━━━━━━━━━━ */}
      <section className="relative py-28 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0d2137] via-[#12304d] to-[#0f2a44]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
          }}
        />
        <WaterRipple />

        <div className="relative z-10 max-w-3xl mx-auto text-center">
          <FadeIn>
            <h2 className="font-display text-4xl sm:text-5xl text-white mb-6 leading-tight">
              Your next trip starts
              <br />
              with better data.
            </h2>
          </FadeIn>
          <FadeIn delay={150}>
            <p className="text-slate-300 text-lg mb-10 max-w-xl mx-auto">
              Join WaterPulse and make every visit to Canada&rsquo;s waterways safer and
              better informed — for free.
            </p>
          </FadeIn>
          <FadeIn delay={300}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/register" className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl text-sm font-bold text-white transition-all duration-200 shadow-lg bg-[#2196f3] hover:bg-[#42a5f5] shadow-blue-900/30 hover:shadow-[#2196f3]/30">
                Create Free Account
                <IconArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
              <Link href="/dashboard" className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl text-sm font-semibold bg-white/10 text-white border border-white/15 hover:bg-white/15 backdrop-blur-sm transition-all duration-200">
                Explore as Guest
              </Link>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ━━━━━━━━━━━━━━━━ FOOTER ━━━━━━━━━━━━━━━━ */}
      <Footer />
    </div>
  );
}
