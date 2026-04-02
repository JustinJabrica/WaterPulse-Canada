import { create } from "zustand";

/**
 * Dashboard state that persists across page navigations.
 *
 * When a user selects a province, searches, or filters on the dashboard,
 * then navigates to a station detail (or future map page) and comes back,
 * the dashboard restores exactly where they left off.
 */
const useDashboardStore = create((set) => ({
  // ── State ─────────────────────────────────
  selectedProvince: null,
  searchQuery: "",
  typeFilter: "all",
  showNoData: false,

  // ── Actions ───────────────────────────────
  setSelectedProvince: (province) => set({ selectedProvince: province }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setTypeFilter: (filter) => set({ typeFilter: filter }),
  setShowNoData: (show) => set({ showNoData: show }),

  /** Reset search and filter (e.g., when switching provinces) */
  clearSearch: () => set({ searchQuery: "", typeFilter: "all" }),
}));

export default useDashboardStore;
