# WaterPulse Frontend

Next.js (App Router) with JavaScript and Tailwind CSS.

## Commands
- `npm run dev` — dev server on port 3000
- `npm run build` — production build
- `npm run lint` — ESLint check

## Architecture
```
src/
├── app/
│   ├── layout.js                        # Root layout, fonts, AuthProvider, modal slot
│   ├── page.js                          # Landing page (/)
│   ├── globals.css                      # Brand tokens, keyframes, utilities
│   ├── dashboard/page.js                # Station cards, search, province picker
│   ├── station/[station_number]/page.js # Station detail (full page, direct navigation)
│   ├── @modal/(.)station/[station_number]/page.js  # Station detail (modal overlay, in-app navigation)
│   ├── @modal/default.js                # Returns null when no modal is active
│   ├── login/page.js                    # Log in
│   └── register/page.js                 # Create account
├── components/
│   ├── WaterPulseLogo.js  # Brand logo (horizontal, stacked, icon-only)
│   ├── Navbar.js          # Site-wide nav, auth-aware, transparent mode
│   ├── Footer.js          # Site-wide footer with nav links + disclaimer
│   ├── StationDetail.js   # Shared station content (readings, weather, percentiles, metadata)
│   ├── StationCard.js     # Card for list views (readings, rating pills, capacity bar)
│   └── RatingPill.js      # Colour-coded rating badge (very low → very high)
├── stores/
│   └── dashboardStore.js  # Zustand store — persists province/search/filter/showNoData across nav
├── context/
│   └── authcontext.js     # AuthProvider — user state, login/register/logout
└── lib/
    ├── api.js             # Fetch wrapper with credentials + CSRF header
    └── constants.js       # Provinces, station types, ratings, WMO codes, AQI, Beaufort scale, DATA_SOURCES
```

## State Management

Uses **Zustand** for state that must survive page navigations. Stores live in `src/stores/`.

- `dashboardStore.js` — selected province, search query, type filter, `showNoData` toggle (show/hide stations without current data, default false). Persists in-memory so navigating to a station detail and back restores the dashboard exactly.
- Guests get temporary state (resets on tab close). Logged-in persistence via cookie-based Zustand `persist` middleware is planned but not yet built.

## Pages

| Route | Status | Key features |
|-------|--------|-------------|
| `/` | Built | Landing page, live stats from API, CTA |
| `/dashboard` | Built | Province picker, station cards with rating pills + capacity bars, province-scoped search (debounced), station type filter, show inactive stations toggle, auto-refresh every 5 min |
| `/station/[station_number]` | Built | Full readings (flow/level/elevation), percentile bars, capacity bar for reservoirs, weather card (temp/wind+Beaufort/AQI/UV), 7-day forecast, station metadata, auto-refresh. Works as both full page (direct URL) and modal overlay (in-app navigation via intercepting routes) |
| `/login` | Placeholder | |
| `/register` | Placeholder | |
| `/map` | Not started | Interactive Leaflet map |
| `/favourites` | Not started | Saved stations (auth + guest cookie fallback) |
| `/advanced-data` | Not started | Historical data explorer |
| `/about` | Not started | |
| `/contact` | Not started | |

Station detail uses Next.js **intercepting routes** via the `@modal` parallel route slot. When a user clicks a station from the dashboard, the detail loads as a modal overlay on top of the existing page. Direct URL access or hard refresh loads the full page version. Both use the shared `StationDetail` component.

## Components

### StationDetail
Shared component used by both the full station page and the modal overlay. Accepts `stationNumber`, `onClose`, and `refreshButton` props. Contains:
- Station header with name, number, type, province, data source label
- Current readings stat row (flow, level/elevation, outflow, capacity)
- Percentile bars with P25-P75 zone and current value marker
- Capacity progress bar for reservoir stations (colour-coded: red/amber/green/blue/purple)
- Weather card (fetched separately via `GET /api/stations/{id}/weather`): Temperature (with feels-like), Wind (speed + gusts + Beaufort scale), Air Quality Index (with category label), UV Index. Description row shows weather description, humidity, visibility. Shows a loading spinner while weather is being fetched.
- 7-day forecast cards
- Station metadata grid
- Auto-refresh every 5 minutes

### StationCard
Displays station name, number, type, latest readings (flow, level/elevation, capacity), individual rating pills for flow and level, a capacity progress bar for lake/reservoir stations, and freshness timestamp. Links to `/station/{station_number}`. Weather is not shown on cards (fetched on demand in StationDetail only).

- Lake/reservoir stations (`station_type === "L"`) show "Elevation" instead of "Level"
- Capacity bar colour matches rating thresholds (red/amber/green/blue/purple)
- Stations without current data are hidden by default; visible when `showNoData` is toggled in the dashboard store

### RatingPill
Accepts a `rating` prop (lowercase string from backend: "very low", "low", "average", "high", "very high") and renders a colour-coded badge using `RATING_CONFIG` from constants.

### Navbar
Two modes: `transparent` (over dark hero, solidifies on scroll) and solid (default for inner pages). Auth-aware.

### Footer
Dark navy footer with nav links, data disclaimer (ECCC + provincial sources), and copyright.

## API Client (`src/lib/api.js`)
- Every request uses `credentials: "include"` so cookies are sent
- POST/PUT/PATCH/DELETE requests read the `csrf_token` cookie and send it as `X-CSRF-Token` header
- The frontend never reads, stores, or parses the JWT
- Convenience methods: `api.get()`, `api.post()`, `api.put()`, `api.patch()`, `api.del()`

## Auth (`src/context/authcontext.js`)
- On mount, calls `GET /api/auth/me` to check for existing session
- Exposes: `user`, `isLoading`, `isAuthenticated`, `login()`, `register()`, `logout()`
- Wrap the app in `<AuthProvider>` in the root layout

## API Endpoints Used by Frontend

### Dashboard
- `GET /api/stations/provinces` — province list with station counts
- `GET /api/readings/by-province/{code}` — stations with latest readings (also used to derive `lastUpdated` from `fetched_at` timestamps)
- `GET /api/stations/search?q=X&province=Y&limit=50` — province-scoped search (returns StationWithReading)
- `POST /api/readings/refresh?province=X` — trigger on-demand refresh

### Station Detail
- `GET /api/stations/{number}/current` — station with reading and percentiles
- `GET /api/stations/{number}/weather` — cached weather (fetched on demand, <30 min TTL)
- `POST /api/readings/refresh?station_numbers=X` — refresh single station

### Landing Page
- `GET /api/admin/status` — station counts for stats bar

## Constants (`src/lib/constants.js`)

- `PROVINCES` — province code to full name mapping
- `STATION_TYPES` — R/L/M to human labels
- `WMO_DESCRIPTIONS` — weather code to description mapping
- `RATING_CONFIG` — rating label to colour/dot classes
- `DATA_SOURCES` — provider code to display name (e.g., `alberta` → "Rivers Alberta", `eccc` → "ECCC")
- `getAqiCategory(aqi)` — returns `{ label, color }` for US AQI value
- `getBeaufortScale(windSpeedKmh)` — returns `{ force, maxKmh, label }` using Environment Canada km/h thresholds (Beaufort 0–12)

## Data Display Conventions

- Lake/reservoir stations: "Elevation" instead of "Level"
- StationDetail decimals: Flow/Level/Outflow 3dp, Capacity/Temperature/Wind 1dp, AQI/UV 0dp (StatBlock accepts `decimals` prop, default 3)
- StationCard decimals: Flow 1dp, Level 1dp, Capacity 0dp
- Flow units: m³/s, Level/Elevation: m, Capacity: %
- WMO weather codes mapped to human descriptions in `constants.js`
- Beaufort Wind Scale: force 0 (Calm, ≤1 km/h) through force 12 (Hurricane Force, >117 km/h), displayed as "Beaufort {force} — {label}" in wind stat block
- AQI categories: Good (0-50), Moderate (51-100), Sensitive (101-150), Unhealthy (151-200), Very Unhealthy (201-300), Hazardous (301+)
- Rating thresholds: Very Low (<P10), Low (P10-P25), Average (P25-P75), High (P75-P90), Very High (>P90)
- Reservoir fullness: fixed scale (Very Low <20%, Low 20-39%, Average 40-70%, High 71-90%, Very High >90%)

## Design System
- Brand colours: `#1e6ba8` (deep blue), `#2196f3` (bright blue), `#64b5f6` (light blue), `#e3f2fd` (pale blue)
- Fonts: DM Serif Display (headings), Plus Jakarta Sans (body)
- Dark sections: navy gradients `#0d2137` → `#0f2a44`
- Logo on dark backgrounds: wrap in `.logo-on-dark` CSS class
- Rating pills: Very Low (red), Low (amber), Average (emerald), High (blue), Very High (purple)
- Text: plain black (`text-slate-900`) for most content; coloured elements are RatingPills, precipitation (blue), AQI categories, and brand blue links/hovers

## Rules
- All backend calls go through `src/lib/api.js` — never use raw `fetch()` or bare `axios`
- NEVER store tokens in `localStorage` or `sessionStorage`
- Use Canadian English: favourites, colours, metres
- `.env.local` contains `NEXT_PUBLIC_API_URL` — never commit it
- State that must survive navigation goes in Zustand stores (`src/stores/`), not `useState`
