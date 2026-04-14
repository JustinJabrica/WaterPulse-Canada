import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Map page state that persists across navigations and page refreshes.
 *
 * Tracks viewport, filters, loaded stations, popup selection,
 * and multi-station selection for the aggregated summary panel.
 *
 * The `persist` middleware saves selected stations, viewport, and filters
 * to sessionStorage so they survive page refreshes within the same tab.
 * Transient state (stations array, loading, error) is excluded via
 * `partialize` — it's re-fetched from the API on each load.
 */
const useMapStore = create(
  persist(
    (set, get) => ({
      // ── Viewport ─────────────────────────────
      viewState: { latitude: 56.0, longitude: -96.0, zoom: 4 },

      // ── Filters ──────────────────────────────
      provinceFilter: null,
      typeFilter: "all",
      favouritesOnly: false,
      collectionFilter: null,
      showNoData: false,

      // ── Station data from bbox endpoint ──────
      stations: [],
      isLoading: false,
      error: null,

      // ── Single popup (click a marker) ────────
      selectedStationNumber: null,

      // ── Multi-selection (aggregated summary) ─
      selectedStations: [],

      // ── Actions ──────────────────────────────
      setViewState: (viewState) => set({ viewState }),
      setProvinceFilter: (province) => set({ provinceFilter: province }),
      setTypeFilter: (filter) => set({ typeFilter: filter }),
      setFavouritesOnly: (enabled) => set({ favouritesOnly: enabled }),
      setCollectionFilter: (collection) => set({ collectionFilter: collection }),
      setShowNoData: (show) => set({ showNoData: show }),
      setStations: (stations) => {
        // Refresh selected stations with the latest data from the API
        // so the summary panel always shows current readings/ratings.
        const stationMap = new Map(
          stations.map((s) => [s.station_number, s])
        );
        const refreshed = get().selectedStations.map(
          (s) => stationMap.get(s.station_number) || s
        );
        set({ stations, selectedStations: refreshed });
      },
      setIsLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setSelectedStationNumber: (stationNumber) =>
        set({ selectedStationNumber: stationNumber }),

      /** Add or remove a station from the multi-selection set. */
      toggleStationSelection: (station) => {
        const current = get().selectedStations;
        const exists = current.some(
          (s) => s.station_number === station.station_number
        );
        if (exists) {
          set({
            selectedStations: current.filter(
              (s) => s.station_number !== station.station_number
            ),
          });
        } else {
          set({ selectedStations: [...current, station] });
        }
      },

      /** Clear all selected stations. */
      clearSelection: () => set({ selectedStations: [] }),

      /** Reset viewport to default Canada-wide view. */
      resetView: () =>
        set({ viewState: { latitude: 56.0, longitude: -96.0, zoom: 4 } }),
    }),
    {
      name: "waterpulse-map",
      storage: {
        getItem: (name) => {
          if (typeof window === "undefined") return null;
          const value = sessionStorage.getItem(name);
          return value ? JSON.parse(value) : null;
        },
        setItem: (name, value) => {
          if (typeof window === "undefined") return;
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          if (typeof window === "undefined") return;
          sessionStorage.removeItem(name);
        },
      },
      // Only persist state that should survive refresh — not transient API data
      partialize: (state) => ({
        viewState: state.viewState,
        provinceFilter: state.provinceFilter,
        typeFilter: state.typeFilter,
        favouritesOnly: state.favouritesOnly,
        collectionFilter: state.collectionFilter,
        showNoData: state.showNoData,
        selectedStations: state.selectedStations,
        selectedStationNumber: state.selectedStationNumber,
      }),
    }
  )
);

export default useMapStore;
