"use client";

import Link from "next/link";
import RatingPill from "@/components/RatingPill";
import AddToCollectionMenu from "@/components/AddToCollectionMenu";
import { STATION_TYPES } from "@/lib/constants";

/**
 * Station card for list views. Shows station name, type, latest
 * reading values, rating pills, and capacity bar.
 *
 * Props: station — a StationWithReading object from the API.
 */
export default function StationCard({ station }) {
  const reading = station.latest_reading;
  const typeLabel = STATION_TYPES[station.station_type] || station.station_type;
  const isLake = station.station_type === "L";
  const levelLabel = isLake ? "Elevation" : "Level";

  // Reading time (backend sends naive UTC — append Z so JS converts to local)
  const readingTime = reading?.datetime_utc
    ? new Date(reading.datetime_utc.endsWith("Z") ? reading.datetime_utc : reading.datetime_utc + "Z")
    : null;

  return (
    <Link
      href={`/station/${station.station_number}`}
      className="group block min-w-0 overflow-hidden rounded-xl border border-slate-200/80 bg-white p-4 transition-all duration-200 hover:shadow-lg hover:shadow-slate-900/5 hover:border-[#2196f3]/30 hover:-translate-y-0.5"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-slate-900 text-sm leading-tight truncate group-hover:text-[#1e6ba8] transition-colors">
            {station.station_name}
          </h3>
          <p className="text-xs text-slate-900 mt-0.5">
            {station.station_number}
            {typeLabel && <span className="ml-1.5">&middot; {typeLabel}</span>}
          </p>
        </div>
        <div className="shrink-0 -mr-1.5">
          <AddToCollectionMenu
            stationNumber={station.station_number}
            variant="sm"
          />
        </div>
      </div>

      {/* Reading values with individual rating pills */}
      {reading && (
        <div className="space-y-1.5 mb-2">
          {reading.discharge != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-900">
                <span>Flow</span>{" "}
                <span className="font-medium">{reading.discharge.toFixed(1)} m³/s</span>
              </span>
              <RatingPill rating={reading.flow_rating} />
            </div>
          )}
          {/* Outflow — shown for dam/reservoir stations that report outflow
              separately from discharge. No rating pill since the backend
              does not compute percentile ratings for outflow. */}
          {reading.outflow != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-900">
                <span>Outflow</span>{" "}
                <span className="font-medium">{reading.outflow.toFixed(1)} m³/s</span>
              </span>
            </div>
          )}
          {reading.water_level != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-900">
                <span>{levelLabel}</span>{" "}
                <span className="font-medium">{reading.water_level.toFixed(1)} m</span>
              </span>
              <RatingPill rating={reading.level_rating} />
            </div>
          )}
          {/* Capacity bar for lake/reservoir stations */}
          {isLake && reading.pct_full != null && (
            <div className="text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-900">Capacity</span>
                <span className="font-medium text-slate-900">{reading.pct_full.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    reading.pct_full < 20
                      ? "bg-red-400"
                      : reading.pct_full < 40
                        ? "bg-amber-400"
                        : reading.pct_full <= 70
                          ? "bg-emerald-400"
                          : reading.pct_full <= 90
                            ? "bg-blue-400"
                            : "bg-purple-400"
                  }`}
                  style={{ width: `${Math.min(reading.pct_full, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Freshness */}
      <div className="flex items-center justify-end text-xs text-slate-900">
        {!reading && <span className="mr-auto">No reading available</span>}
        {readingTime && (
          <span title={readingTime.toLocaleString()}>
            {readingTime.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
          </span>
        )}
      </div>
    </Link>
  );
}
