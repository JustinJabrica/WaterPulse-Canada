# WaterPulse Frontend

Next.js 16 (App Router) with JavaScript, React 19, and Tailwind CSS 4.

## Commands
- `npm run dev` — dev server on port 3000 (Turbopack)
- `npm run build` — production build
- `npm run start` — serve production build
- `npm run lint` — ESLint check

## Architecture
```
src/
├── app/
│   ├── layout.js                        # Root layout, fonts, AuthProvider, modal slot
│   ├── page.js                          # Landing page (/)
│   ├── globals.css                      # Brand tokens, keyframes, utility classes
│   ├── dashboard/page.js                # Station cards, search, province picker
│   ├── station/[station_number]/page.js # Station detail (full page, direct URL)
│   ├── @modal/(.)station/[station_number]/page.js  # Station detail (modal overlay)
│   ├── @modal/default.js                # Returns null when no modal is active
│   ├── login/page.js                    # Log in
│   └── register/page.js                 # Create account
├── components/
│   ├── WaterPulseLogo.js    # Brand logo (horizontal, stacked, icon-only)
│   ├── Navbar.js            # Site-wide nav, auth-aware, transparent mode
│   ├── Footer.js            # Site-wide footer with nav links + disclaimer
│   ├── StationDetail.js     # Shared station content (readings, weather, metadata)
│   ├── StationCard.js       # Card for list views (readings, pills, capacity bar)
│   └── RatingPill.js        # Colour-coded rating badge
├── stores/
│   └── dashboardStore.js    # Zustand — persists dashboard state across navigation
├── context/
│   └── authcontext.js       # AuthProvider — user state, login/register/logout
└── lib/
    ├── api.js               # Fetch wrapper with credentials + CSRF header
    └── constants.js          # Provinces, station types, ratings, WMO codes, AQI, Beaufort
```

## Connecting to the Backend

The frontend calls the FastAPI backend at the URL set in `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000` in development).

Create a `.env.local` file in the frontend root:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Important:** `.env.local` contains configuration and should never be committed to version control. It is listed in `.gitignore` by default.

## Authentication

Auth is handled entirely via HTTPOnly cookies. The frontend never reads, stores, or parses the JWT — the browser and backend manage it.

### How It Works

1. User submits credentials — frontend calls `POST /api/auth/login` via `api.post()`
2. Backend sets two cookies in the response headers:
   - `access_token` — HTTPOnly (invisible to JavaScript, sent automatically by the browser)
   - `csrf_token` — plain cookie (readable by JavaScript for CSRF protection)
3. Frontend calls `GET /api/auth/me` — backend reads cookie, returns user object
4. All subsequent requests use `credentials: "include"` so the browser attaches cookies automatically
5. Logout: `POST /api/auth/logout` — backend clears both cookies

### CSRF Protection

On every POST, PUT, PATCH, and DELETE request, the API client (`src/lib/api.js`) reads the `csrf_token` cookie and sends it as an `X-CSRF-Token` header. The backend compares the header to the cookie value and rejects requests that don't match.

### AuthContext (`src/context/authcontext.js`)

Wrap the app in `<AuthProvider>` (done in `layout.js`) to access auth state anywhere:

```jsx
import { useAuth } from "@/context/authcontext";

const { user, isLoading, isAuthenticated, login, register, logout } = useAuth();
```

- On mount, calls `GET /api/auth/me` to check for an existing session
- `login(email, password)` — authenticates and sets user state
- `register(name, email, password)` — creates account and sets user state
- `logout()` — clears cookies and resets to guest

## State Management

Uses **Zustand** for state that must survive client-side page navigations (e.g., dashboard province/search/filter selection persists when viewing a station and navigating back).

Stores live in `src/stores/`. Currently in-memory only (resets on tab close), which is intentional for guest users. Cookie-based persistence for logged-in users is planned.

```jsx
import useDashboardStore from "@/stores/dashboardStore";

const selectedProvince = useDashboardStore((s) => s.selectedProvince);
const setSelectedProvince = useDashboardStore((s) => s.setSelectedProvince);
```

### What Zustand Is

Zustand is a small, fast state management library for React. Unlike `useState` (which resets when a component unmounts), Zustand stores live outside the React component tree. This means:

- State **survives page navigations** — navigating to a station detail and back doesn't reset the dashboard
- State is **shared across components** — any component can read or write to the store without prop drilling
- State is **in-memory** — it lives in a JavaScript variable, not localStorage or cookies (so it resets on tab close)

Think of it like a global variable that React components can subscribe to. When the variable changes, only the components that use that specific piece of state re-render.

### Dashboard Store (`src/stores/dashboardStore.js`)

| State | Type | Default | Purpose |
|-------|------|---------|---------|
| `selectedProvince` | `string \| null` | `null` | Currently selected province code (e.g., "AB") |
| `searchQuery` | `string` | `""` | Current search text |
| `typeFilter` | `string` | `"all"` | Station type filter ("all", "R", "L", "M") |
| `showNoData` | `boolean` | `false` | Whether to show stations without current data |

Actions: `setSelectedProvince()`, `setSearchQuery()`, `setTypeFilter()`, `setShowNoData()`, `clearSearch()` (resets query and filter).

## Station Detail — Modal Overlay and Full Page

The station detail view uses Next.js **intercepting routes** and **parallel routes** to support two display modes from the same component:

### How It Works

1. **In-app navigation** (clicking a station card on the dashboard) — the station detail loads as a **modal overlay** on top of the existing page. The dashboard stays rendered behind it, preserving scroll position and state.

2. **Direct URL access** (pasting a URL or hard refresh) — the station detail loads as a **full page** since there's no background page to overlay on.

Both modes render the same `StationDetail` component with the same data. The difference is just how it's presented.

### The Files Involved

```
src/app/
├── station/[station_number]/page.js    # Full page version (direct URL)
├── @modal/(.)station/[station_number]/page.js  # Modal overlay version (in-app navigation)
├── @modal/default.js                   # Returns null when no modal is active
└── layout.js                           # Renders {children} and {modal} slots
```

### What Each Piece Does

**`layout.js`** — The root layout accepts two slots: `children` (the main page content) and `modal` (the overlay). It renders both:

```jsx
function RootLayout({ children, modal }) {
  return (
    <html>
      <body>
        {children}
        {modal}
      </body>
    </html>
  );
}
```

**`@modal/default.js`** — Returns `null`. This tells Next.js "when no modal is active, render nothing in the modal slot." Without this file, navigating to any non-station page would error.

**`@modal/(.)station/[station_number]/page.js`** — The `(.)` prefix is the **intercepting route** syntax. It means: "when a navigation to `/station/[station_number]` happens from within the app, intercept it and render this component instead of the full page version." This file wraps `StationDetail` in a modal container with:
- Dark backdrop (click to close)
- Escape key to close
- Scroll lock on the body
- Slide-up animation
- Sticky header with back and close buttons

**`station/[station_number]/page.js`** — The normal full-page route. Used when the URL is accessed directly (bookmarks, shared links, page refresh). Renders `StationDetail` with a back button.

### Why This Pattern?

The alternative would be to unmount the dashboard, load the station page, then remount the dashboard when going back. This loses scroll position, resets loading states, and requires re-fetching data. The modal overlay keeps the dashboard alive and ready.

## Components

### StationDetail (`src/components/StationDetail.js`)

Shared component used by both the full station page and the modal overlay. Accepts three props:

| Prop | Type | Default | Purpose |
|------|------|---------|---------|
| `stationNumber` | `string` | required | The station ID to fetch |
| `onClose` | `function` | `undefined` | Called when back/close is clicked (if not provided, back button is hidden) |
| `refreshButton` | `boolean` | `true` | Whether to show the refresh button |

Contains:
- **Station header** — name, number, type, province, data source label (Rivers Alberta or ECCC)
- **Current Readings card** — stat row (flow, level/elevation, outflow, capacity), percentile bars with P25-P75 average zone and current value marker, capacity progress bar for reservoir stations (colour-coded: red < 20%, amber < 40%, green <= 70%, blue <= 90%, purple > 90%)
- **Weather and Air Quality card** — fetched separately via `GET /api/stations/{id}/weather` (not bundled with the station readings request). Shows its own loading spinner while weather data is being fetched. Contains four stat blocks:
  - Temperature (with feels-like)
  - Wind (speed + gusts + Beaufort scale classification, e.g., "Beaufort 4 — Moderate Breeze")
  - Air Quality Index (AQI number + category label like "Good" or "Moderate")
  - UV Index
  - Description row: weather description, humidity, visibility
- **7-day Forecast card** — day name, high/low temps, weather description, precipitation amount
- **Station Information card** — metadata grid (station number, type, province, data source, basin, catchment, coordinates, etc.)
- Auto-refresh every 5 minutes while the page is visible

#### Decimal Places

StationDetail uses a `StatBlock` component that accepts a `decimals` prop to control how many decimal places each value displays:

| Measurement | Decimal Places |
|-------------|---------------|
| Flow (m³/s) | 3 |
| Level / Elevation (m) | 3 |
| Outflow (m³/s) | 3 |
| Capacity (%) | 1 |
| Temperature (°C) | 1 |
| Wind (km/h) | 1 |
| AQI | 0 |
| UV Index | 0 |

### StationCard (`src/components/StationCard.js`)

Card for station list views. Displays:
- Station name, number, and type
- Latest readings: flow (m³/s, 1 decimal), level/elevation (m, 1 decimal), with individual rating pills
- Capacity progress bar for lake/reservoir stations (colour-coded by fullness)
- Data freshness timestamp (reading time, converted from UTC to local)

Weather is **not** shown on station cards — it is only fetched and displayed in StationDetail. The `WMO_DESCRIPTIONS` import is not used in this component.

Lake/reservoir stations show "Elevation" instead of "Level". Links to `/station/{station_number}`.

Stations without current reading data are hidden by default on the dashboard. The "Show Inactive Stations" toggle (controlled by `showNoData` in the Zustand store) reveals them.

### RatingPill (`src/components/RatingPill.js`)

Colour-coded badge for flow/level/capacity ratings. Accepts a `rating` prop (lowercase string from the backend).

| Rating | Colour |
|--------|--------|
| Very Low | Red |
| Low | Amber |
| Average | Emerald |
| High | Blue |
| Very High | Purple |

### Navbar (`src/components/Navbar.js`)

Site-wide navigation bar with two modes:

| Prop | Default | Behaviour |
|------|---------|-----------|
| `transparent` | `false` | When `true`, starts see-through over dark hero sections and turns solid white on scroll. When `false`, always solid (inner pages). |

Auth-aware: shows "Log In / Get Started" for guests, "Dashboard / Log Out" for authenticated users.

```jsx
<Navbar transparent />  {/* Landing page — over dark hero */}
<Navbar />               {/* Inner pages — always solid */}
```

### Footer (`src/components/Footer.js`)

Dark navy footer with navigation links, ECCC and provincial data disclaimer, and dynamic copyright year.

### WaterPulseLogo (`src/components/WaterPulseLogo.js`)

Brand logo with river wave SVG and text. Supports three variants and four sizes:

| Prop | Options | Default |
|------|---------|---------|
| `variant` | `"horizontal"`, `"stacked"`, `"icon-only"` | `"horizontal"` |
| `size` | `"small"`, `"medium"`, `"large"`, `"xlarge"` | `"medium"` |

On dark backgrounds, wrap in a container with class `logo-on-dark` to shift colours to lighter variants.

## API Client (`src/lib/api.js`)

All backend requests go through this Axios-based wrapper. Never use raw `fetch()` or bare `axios` for backend calls.

Built on an Axios instance with:
- `withCredentials: true` — cookies sent on every request automatically
- **Request interceptor** — attaches the `X-CSRF-Token` header on POST/PUT/PATCH/DELETE
- **Response interceptor** — unwraps `response.data` so callers get the payload directly, and normalizes errors into `{ message, status }`

```jsx
import api from "@/lib/api";

const stations = await api.get("/api/stations/");
await api.post("/api/favorites/", { station_number: "05BH004" });
await api.del("/api/favorites/05BH004");
```

Methods: `api.get()`, `api.post()`, `api.put()`, `api.patch()`, `api.del()`

## Constants (`src/lib/constants.js`)

This file contains all the lookup tables and utility functions the frontend uses to interpret backend data.

### Lookup Tables

| Export | Purpose |
|--------|---------|
| `PROVINCES` | Province code to full name (e.g., `"AB"` to `"Alberta"`) |
| `STATION_TYPES` | Station type code to label (`"R"` to `"River"`, `"L"` to `"Lake / Reservoir"`, `"M"` to `"Meteorological"`) |
| `WMO_DESCRIPTIONS` | WMO weather code number to human description (e.g., `0` to `"Clear sky"`, `95` to `"Thunderstorm"`) |
| `RATING_CONFIG` | Rating label to Tailwind colour classes for pills and dots |
| `DATA_SOURCES` | Provider code to display name (`"alberta"` to `"Rivers Alberta"`, `"eccc"` to `"ECCC"`) |

### Utility Functions

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `getAqiCategory(aqi)` | US AQI number (0-500) | `{ label, color }` | Returns the AQI category name (e.g., "Good", "Moderate") and a Tailwind text colour class |
| `getBeaufortScale(windSpeedKmh)` | Wind speed in km/h | `{ force, maxKmh, label }` | Returns the Beaufort scale force number (0-12) and description (e.g., "Moderate Breeze") based on Environment Canada's km/h thresholds |

## Pages

| Route | Status | Key Features |
|-------|--------|-------------|
| `/` | Built | Landing page with live stats, hero, feature sections |
| `/dashboard` | Built | Province picker, station cards with rating pills + capacity bars, province-scoped search with debounce, station type filter (All/River/Lake/Met), show inactive stations toggle, active station count by type in province header, auto-refresh every 5 min |
| `/station/[station_number]` | Built | Full readings (flow/level/elevation), percentile bars with P25-P75 zone, capacity bar for reservoirs, weather card (temp/wind+Beaufort/AQI/UV — fetched separately with its own loading spinner), 7-day forecast, station metadata, data source label, auto-refresh. Works as modal overlay (in-app) or full page (direct URL) |
| `/login` | Placeholder | |
| `/register` | Placeholder | |
| `/map` | Not started | Interactive Leaflet map |
| `/favourites` | Not started | Saved stations (auth + guest cookie fallback) |
| `/advanced-data` | Not started | Historical data explorer |
| `/about` | Not started | |
| `/contact` | Not started | |

## Dashboard Features

### Province Picker

Buttons for each province, sorted by total station count (largest first). Each button shows the province code and total station count. The selected province is highlighted in blue.

### Province Header

Shows the province name with a breakdown of active stations: "{X} River and {Y} Lake/Reservoir Stations Active". Also shows the last updated timestamp, derived from the most recent `fetched_at` across loaded station readings (not from a separate API call).

### Province-Scoped Search

The search bar sends queries to `GET /api/stations/search?q=X&province=Y&limit=50`, scoping results to the currently selected province. Search is debounced at 300ms. The search re-runs automatically if the province changes while a search query is active.

### Station Type Filter

Filter buttons for All, River, Lake/Reservoir, and Meteorological. Each shows a count badge. The counts reflect the total stations (including inactive), while the grid only shows stations matching the current filter AND the `showNoData` toggle.

### Show Inactive Stations Toggle

A toggle button that shows/hides stations without current reading data. Default is off (inactive stations hidden). Shows a badge with the count of hidden stations. State persists in Zustand across navigation.

### Auto-Refresh

The dashboard auto-refreshes readings every 5 minutes while the page is visible (uses `document.visibilityState`). A manual refresh button is also available.

## Timestamp Handling

The backend stores all timestamps as naive UTC (no timezone info). The frontend handles conversion to the user's local timezone:

1. Backend sends timestamps like `"2026-04-01T14:30:00"` (no Z suffix)
2. Frontend appends "Z" before creating a `Date` object: `new Date(ts + "Z")`
3. JavaScript's `Date` then knows it's UTC and converts to local time for display

This happens in both `StationCard` (for reading time) and `StationDetail` (for reading time and fetched_at).

## Design System

### Colours

| Token | Hex | Usage |
|-------|-----|-------|
| Deep blue | `#1e6ba8` | Primary brand, headings, icons |
| Bright blue | `#2196f3` | CTAs, accents, hover states |
| Light blue | `#64b5f6` | Gradient endpoints, secondary |
| Pale blue | `#e3f2fd` | Backgrounds, light fills |
| Navy dark | `#0d2137` to `#0f2a44` | Hero gradients, footer |

### Typography

Loaded via `next/font/google` in `layout.js` (self-hosted, no external requests):

| Font | CSS Variable | Usage |
|------|-------------|-------|
| DM Serif Display | `--font-display` | Headings (`.font-display` class) |
| Plus Jakarta Sans | `--font-body` | Body text (default) |

### Text Colours

Most text across StationCard, StationDetail, and the dashboard uses plain black (`text-slate-900`). Coloured text is reserved for:
- **RatingPills** — colour-coded by rating (red/amber/emerald/blue/purple)
- **Precipitation** — blue (`text-blue-500`) in the 7-day forecast
- **AQI categories** — coloured by severity (from `getAqiCategory`)
- **Brand blue** — interactive elements (links, hover states, clear search)
- **Placeholder text** — search input (`placeholder:text-slate-400`)
- **Dash** — missing values (`text-slate-300`)

## Frontend Interpretation of Backend Data

The backend sends raw numerical values. The frontend interprets them into user-friendly categories:

### WMO Weather Codes
| Code Range | Meaning |
|-----------|---------|
| 0-3 | Clear / cloudy |
| 45-48 | Fog |
| 51-57 | Drizzle |
| 61-67 | Rain |
| 71-77 | Snow |
| 80-86 | Showers |
| 95-99 | Thunderstorm |

### Beaufort Wind Scale
| Force | Max km/h | Description |
|-------|----------|-------------|
| 0 | 1 | Calm |
| 1 | 5 | Light Air |
| 2 | 11 | Light Breeze |
| 3 | 19 | Gentle Breeze |
| 4 | 28 | Moderate Breeze |
| 5 | 38 | Fresh Breeze |
| 6 | 49 | Strong Breeze |
| 7 | 61 | Near Gale |
| 8 | 74 | Gale |
| 9 | 88 | Strong Gale |
| 10 | 102 | Storm |
| 11 | 117 | Violent Storm |
| 12 | -- | Hurricane Force |

Thresholds from Environment Canada. Displayed in the StationDetail wind stat block as "Beaufort {force} — {label}".

### Visibility (metres)
| Range | Category |
|-------|----------|
| < 200m | Dense fog |
| < 1,000m | Foggy |
| < 4,000m | Mildly foggy |
| < 10,000m | Clear |
| > 10,000m | Very clear |

### Air Quality (US AQI)
| Range | Category |
|-------|----------|
| 0-50 | Good |
| 51-100 | Moderate |
| 101-150 | Unhealthy for sensitive groups |
| 151-200 | Unhealthy |
| 201-300 | Very unhealthy |
| 301+ | Hazardous |

### Rating Thresholds
| Rating | Flow/Level (percentile) | Reservoir Fullness (fixed) |
|--------|------------------------|---------------------------|
| Very Low | < P10 | < 20% |
| Low | P10 - P25 | 20 - 39% |
| Average | P25 - P75 | 40 - 70% |
| High | P75 - P90 | 71 - 90% |
| Very High | > P90 | > 90% |

## Rules
- All backend calls go through `src/lib/api.js` — never use raw `fetch()` or bare `axios`
- NEVER store tokens in `localStorage` or `sessionStorage`
- Use Canadian English: favourites, colours, metres
- `.env.local` contains `NEXT_PUBLIC_API_URL` — never commit it
- State that must survive navigation goes in Zustand stores (`src/stores/`), not `useState`
