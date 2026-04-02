import Link from "next/link";
import WaterPulseLogo from "@/components/WaterPulseLogo";

const NAV_LINKS = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Map", href: "/map" },
  { label: "Favourites", href: "/favourites" },
  { label: "Advanced Data", href: "/advanced-data" },
  { label: "About", href: "/about" },
  { label: "Contact", href: "/contact" },
];

/**
 * Footer — shared site-wide footer with navigation, data disclaimer,
 * and copyright.  Uses the dark colour scheme from the landing page.
 */
export default function Footer() {
  return (
    <footer className="bg-[#0b1a2a] border-t border-slate-800 py-12 px-6">
      <div className="max-w-5xl mx-auto">
        {/* Top row — logo + nav links */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8 mb-10">
          <div className="logo-on-dark flex items-center gap-1.5">
            <WaterPulseLogo variant="horizontal" size="small" />
            <span className="text-slate-500 text-sm ml-1">Canada</span>
          </div>

          <nav className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                className="text-slate-400 hover:text-white transition-colors duration-200"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>

        {/* Bottom row — disclaimer + copyright */}
        <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500 leading-relaxed max-w-2xl">
            Water data is provisional and sourced from Environment and Climate Change
            Canada (ECCC) and provincial networks including the Government of Alberta. It
            has not been reviewed for accuracy and may be subject to change. WaterPulse
            assumes no responsibility for data accuracy. Use at your own risk.
          </p>
          <p className="text-xs text-slate-600 shrink-0">
            &copy; {new Date().getFullYear()} WaterPulse
          </p>
        </div>
      </div>
    </footer>
  );
}
