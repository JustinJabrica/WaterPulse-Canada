"use client";

/**
 * WaterPulseLogo — brand logo with river wave SVG + text.
 *
 * Variants: "horizontal" (default), "stacked", "icon-only"
 * Sizes:    "small", "medium" (default), "large", "xlarge"
 *
 * On dark backgrounds, wrap in a container with class "logo-on-dark"
 * to shift colours to lighter variants (see globals.css).
 */

const SIZES = {
  small:  { icon: 32, font: "text-xl",   gap: "gap-2" },
  medium: { icon: 40, font: "text-[28px]", gap: "gap-3" },
  large:  { icon: 60, font: "text-4xl",  gap: "gap-4" },
  xlarge: { icon: 80, font: "text-7xl",  gap: "gap-8" },
};

function LogoIcon({ size }) {
  return (
    <svg
      className="water-wave"
      viewBox="0 0 60 60"
      width={size}
      height={size}
    >
      {/* River curves */}
      <path d="M10,45 Q20,35 30,40 T50,35" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M8,35 Q18,25 28,30 T48,25" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M12,25 Q22,15 32,20 T52,15" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />

      {/* Pulse line */}
      <path
        className="pulse-line"
        d="M5,50 L15,50 L18,40 L22,55 L26,30 L30,50 L35,50 L38,45 L42,50 L55,50"
        fill="none"
        stroke="#2196f3"
        strokeWidth="2.5"
        strokeLinecap="round"
        opacity="0.9"
      />

      {/* Animated pulse dots */}
      <circle className="pulse-dot" cx="30" cy="30" r="2" fill="#2196f3" />
      <circle className="pulse-dot animate-delay-500" cx="42" cy="25" r="1.5" fill="#2196f3" />
      <circle className="pulse-dot animate-delay-1000" cx="20" cy="35" r="1.5" fill="#2196f3" />
    </svg>
  );
}

export default function WaterPulseLogo({
  variant = "horizontal",
  size = "medium",
  className = "",
}) {
  const s = SIZES[size] || SIZES.medium;
  const showText = variant !== "icon-only";

  const direction = variant === "stacked" ? "flex-col" : "flex-row";

  return (
    <div
      className={`waterpulse-logo flex items-center ${direction} ${s.gap} ${className}`}
      style={{ color: "#1e6ba8" }}
    >
      <LogoIcon size={s.icon} />
      {showText && (
        <div className="logo-text" style={{ lineHeight: 1, letterSpacing: "-1px" }}>
          <span className={`${s.font} font-bold`} style={{ color: "#1e6ba8" }}>Water</span>
          <span className={`${s.font} font-bold`} style={{ color: "#2196f3" }}>Pulse</span>
        </div>
      )}
    </div>
  );
}
