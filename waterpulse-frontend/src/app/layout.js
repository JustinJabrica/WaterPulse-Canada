import { DM_Serif_Display, Plus_Jakarta_Sans } from "next/font/google";
import { AuthProvider } from "@/context/authcontext";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata = {
  title: "WaterPulse Canada",
  description:
    "Real-time river, lake, and reservoir conditions across Canada — water levels, flow rates, weather, and air quality for every monitored station.",
};

export default function RootLayout({ children, modal }) {
  return (
    <html lang="en" className={`${dmSerif.variable} ${jakarta.variable}`}>
      <body className="min-h-screen flex flex-col bg-slate-50 text-slate-900 antialiased">
        <AuthProvider>
          {children}
          {modal}
        </AuthProvider>
      </body>
    </html>
  );
}
