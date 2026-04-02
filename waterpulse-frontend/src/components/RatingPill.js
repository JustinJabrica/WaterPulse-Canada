"use client";

import { RATING_CONFIG } from "@/lib/constants";

/**
 * Colour-coded rating badge.
 * Accepts backend rating strings like "very low", "high", etc.
 */
export default function RatingPill({ rating }) {
  if (!rating) return null;

  const config = RATING_CONFIG[rating.toLowerCase()];
  if (!config) return null;

  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.color}`}
    >
      {config.label}
    </span>
  );
}
