"use client";

import { useRouter } from "next/navigation";
import RatingPill from "@/components/RatingPill";
import AddToCollectionMenu from "@/components/AddToCollectionMenu";
import { STATION_TYPES } from "@/lib/constants";
import useMapStore from "@/stores/mapStore";

/**
 * Compact station card for the map popup. Adapted from StationCard
 * but without the Link wrapper — instead provides "View Details"
 * and "Add/Remove Selection" buttons.
 *
 * Props: station — a StationWithReading object from the API.
 */
export default function MapStationCard({ station }) {
  const router = useRouter();
  const reading = station.latest_reading;
  const typeLabel = STATION_TYPES[station.station_type] || station.station_type;
  const isLake = station.station_type === "L";
  const levelLabel = isLake ? "Elevation" : "Level";

  const selectedStations = useMapStore((s) => s.selectedStations);
  const toggleStationSelection = useMapStore((s) => s.toggleStationSelection);

  const isSelected = selectedStations.some(
    (s) => s.station_number === station.station_number
  );

  const readingTime = reading?.datetime_utc
    ? new Date(
        reading.datetime_utc.endsWith("Z")
          ? reading.datetime_utc
          : reading.datetime_utc + "Z"
      )
    : null;

  return (
    <div className="min-w-[240px]">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-3 pr-6">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-slate-900 text-sm leading-tight">
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
                <span className="font-medium">
                  {reading.discharge.toFixed(1)} m³/s
                </span>
              </span>
              <RatingPill rating={reading.flow_rating} />
            </div>
          )}
          {reading.outflow != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-900">
                <span>Outflow</span>{" "}
                <span className="font-medium">
                  {reading.outflow.toFixed(1)} m³/s
                </span>
              </span>
            </div>
          )}
          {reading.water_level != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-900">
                <span>{levelLabel}</span>{" "}
                <span className="font-medium">
                  {reading.water_level.toFixed(1)} m
                </span>
              </span>
              <RatingPill rating={reading.level_rating} />
            </div>
          )}
          {isLake && reading.pct_full != null && (
            <div className="text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-900">Capacity</span>
                <span className="font-medium text-slate-900">
                  {reading.pct_full.toFixed(0)}%
                </span>
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
      <div className="flex items-center justify-end text-xs text-slate-900 mb-2.5">
        {!reading && <span className="mr-auto">No reading available</span>}
        {readingTime && (
          <span title={readingTime.toLocaleString()}>
            {readingTime.toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 pt-2 border-t border-slate-100">
        <button
          onClick={() => router.push(`/station/${station.station_number}`)}
          className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-[#1e6ba8] rounded-lg hover:bg-[#185a8c] transition-colors cursor-pointer"
        >
          View Details
        </button>
        <button
          onClick={() => toggleStationSelection(station)}
          className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer ${
            isSelected
              ? "text-red-700 bg-red-50 border border-red-200 hover:bg-red-100"
              : "text-[#1e6ba8] bg-blue-50 border border-blue-200 hover:bg-blue-100"
          }`}
        >
          {isSelected ? "Remove" : "Select"}
        </button>
      </div>
    </div>
  );
}
