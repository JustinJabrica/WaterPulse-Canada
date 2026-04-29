# WaterPulse Frontend

Next.js 16 (App Router) with JavaScript, React 19, and Tailwind CSS 4.

## Commands
- `npm run dev` — dev server on port 3000 (Turbopack)
- `npm run build` — production build
- `npm run start` — serve production build
- `npm run lint` — ESLint check

## Getting Started

### Local Development
1. `npm install` — install dependencies
2. Create a `.env.local` file with `NEXT_PUBLIC_API_URL=http://localhost:8000`
3. `npm run dev` — starts the dev server on http://localhost:3000

### Docker
1. Copy `.env.example` to `.env` at the **repo root** and fill in secrets
2. Run `docker-compose up --build` from the repo root
3. Open http://localhost (via Caddy) or http://localhost:3000 (direct)

> The Docker setup builds a production image. For live code reloading during development, use the local approach above.

## Architecture
```
src/
├── app/
│   ├── layout.js                        # Root layout, fonts, AuthProvider, modal slot
│   ├── page.js                          # Landing page (/)
│   ├── globals.css                      # Brand tokens, keyframes, utilities, MapLibre CSS
│   ├── dashboard/page.js                # Station cards, search, province picker
│   ├── map/
│   │   ├── page.js                      # Map page, dynamic import, URL state sync
│   │   ├── MapView.js                   # react-map-gl wrapper, GeoJSON layers, clustering, popups
│   │   ├── useMapData.js                # Viewport-based bbox fetch hook (debounced)
│   │   ├── MapFilterPanel.js            # Province dropdown, type toggle, showNoData toggle
│   │   ├── MapLegend.js                 # Collapsible rating colour legend (bottom-right)
│   │   └── SelectionSummaryPanel.js     # Multi-station aggregated summary sidebar
│   ├── station/[station_number]/page.js # Station detail (full page, direct URL)
│   ├── @modal/(.)station/[station_number]/page.js  # Station detail (modal overlay)
│   ├── @modal/default.js                # Returns null when no modal is active
│   ├── login/page.js                    # Log in (redirects if already authenticated)
│   ├── register/page.js                 # Create account (redirects if already authenticated)
│   ├── error.js                         # Global error boundary (catches component crashes)
│   └── not-found.js                     # Custom 404 page (dark hero style)
├── components/
│   ├── WaterPulseLogo.js    # Brand logo (horizontal, stacked, icon-only)
│   ├── Navbar.js            # Site-wide nav, auth-aware, transparent mode
│   ├── Footer.js            # Site-wide footer with nav links + disclaimer
│   ├── StationDetail.js     # Shared station content (readings, weather, metadata)
│   ├── StationCard.js       # Card for list views (readings, pills, capacity bar)
│   ├── MapStationCard.js    # Compact popup card for map (View Details + Select buttons)
│   ├── RatingPill.js        # Colour-coded rating badge
│   └── Toast.js             # Auth toast notifications (success/error, auto-dismiss)
├── stores/
│   ├── dashboardStore.js    # Zustand — persists dashboard state across navigation
│   └── mapStore.js          # Zustand — viewport, filters, selection (sessionStorage persist)
├── context/
│   └── authcontext.js       # AuthProvider — user state, login/register/logout, toast helpers
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

> **Build-time variable:** `NEXT_PUBLIC_API_URL` is baked into the client-side JavaScript at build time (this is a Next.js behaviour for all `NEXT_PUBLIC_*` variables). It **cannot be changed at runtime** — the Docker image must be rebuilt if you need a different URL. The default is `http://localhost:8000`. For production behind Caddy, use the full public domain (e.g. `https://waterpulse.ca`).

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

Stores live in `src/stores/`.

- `dashboardStore.js` — in-memory only (resets on tab close), intentional for guest users. Cookie-based persistence for logged-in users is planned.
- `mapStore.js` — uses Zustand `persist` middleware with `sessionStorage` so map viewport, filters, and station selections survive page refreshes within the same tab. Transient API data (stations array, loading, error) is excluded from persistence.

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

### Map Store (`src/stores/mapStore.js`)

Persisted to `sessionStorage` via Zustand `persist` middleware. Selections and viewport survive page refresh.

| State | Type | Default | Persisted | Purpose |
|-------|------|---------|-----------|---------|
| `viewState` | `object` | `{ latitude: 56.0, longitude: -96.0, zoom: 4 }` | Yes | Map camera position |
| `provinceFilter` | `string \| null` | `null` | Yes | Province filter for bbox queries |
| `typeFilter` | `string` | `"all"` | Yes | Station type filter ("all", "R", "L") |
| `showNoData` | `boolean` | `false` | Yes | Show stations without current readings |
| `favouritesOnly` | `boolean` | `false` | Yes | Filter to favourited stations (not yet functional — favourites are now per-collection, see `/collections`) |
| `collectionFilter` | `string \| null` | `null` | Yes | Active collection id from `?collection={id}` deep-link. Consumed by `useCollectionDeepLink` in `/map/page.js` to fetch the collection and pre-select its stations on the map. |
| `selectedStations` | `array` | `[]` | Yes | Multi-selection for summary panel |
| `selectedStationNumber` | `string \| null` | `null` | Yes | Which marker popup is open |
| `stations` | `array` | `[]` | No | Current viewport stations from API |
| `isLoading` | `boolean` | `false` | No | Fetch in progress |
| `error` | `string \| null` | `null` | No | Last fetch error |
| `provinceCounts` | `array \| null` | `null` | No | Per-province totals + `with_reading` counts (from `/api/stations/provinces`, fetched once on map mount). Used to size per-province cluster markers at low zoom. |

Actions: `setViewState()`, `setProvinceFilter()`, `setTypeFilter()`, `setShowNoData()`, `setFavouritesOnly()`, `setCollectionFilter()`, `setStations()`, `setIsLoading()`, `setError()`, `setProvinceCounts()`, `setSelectedStationNumber()`, `toggleStationSelection()`, `clearSelection()`, `resetView()`.

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
  - Description row: weather description, sunrise/sunset, humidity, visibility
- **7-day Forecast card** — day name, high/low temps, weather description, precipitation amount
- **Station Information card** — metadata grid (station number, type, province, data source, basin, catchment, coordinates, etc.)
- Manual refresh button (backend scheduler keeps data fresh every 10 minutes)

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
- Latest readings: flow (m³/s, 1 decimal), outflow (m³/s, 1 decimal), level/elevation (m, 1 decimal), with individual rating pills for flow and level
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

Auth-aware: shows Dashboard + Map links for all users. Authenticated users get a username dropdown (Profile, Log Out); guests see a single Log In button.

On mobile (below `sm` breakpoint) the links collapse into a hamburger menu. Both the mobile menu and the username dropdown close when clicking outside the navbar.

```jsx
<Navbar transparent />  {/* Landing page — over dark hero */}
<Navbar />               {/* Inner pages — always solid */}
```

### Toast (`src/components/Toast.js`)

Auth-scoped toast notifications. Reads `toast` and `dismissToast` from `AuthContext` and renders a fixed-position card at the top of the viewport when a toast is active. Two types:

- `success` — neutral white card (default)
- `error` — red-tinted card

Auto-dismisses after 3 seconds. Clicking the X dismiss button cancels the pending auto-clear timer. Triggered via `AuthContext.showToast(message, type)`; currently fires from `logout()` — "You have been logged out" on success, "Logged out locally — server could not be reached" on network failure.

Rendered once at the root in `src/app/layout.js`.

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
const collections = await api.get("/api/collections/");
await api.post(`/api/collections/${id}/stations`, { station_numbers: ["05BH004"] });
await api.del(`/api/collections/${id}/stations/05BH004`);
```

Methods: `api.get()`, `api.post()`, `api.put()`, `api.patch()`, `api.del()`

## Constants (`src/lib/constants.js`)

This file contains all the lookup tables and utility functions the frontend uses to interpret backend data.

### Lookup Tables

| Export | Purpose |
|--------|---------|
| `PROVINCES` | Province code to full name (e.g., `"AB"` to `"Alberta"`) |
| `STATION_TYPES` | Station type code to label (`"R"` to `"River"`, `"L"` to `"Lake / Reservoir"`) — meteorological excluded |
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
| `/dashboard` | Built | Province picker (alphabetical), station cards with rating pills + outflow + capacity bars, province-scoped search with debounce, station type filter (All/River/Lake), show inactive stations toggle, active station count by type in province header, manual refresh button, infinite scroll (15 stations per page), memoized filter chains |
| `/station/[station_number]` | Built | Full readings (flow/level/elevation/outflow), percentile bars with P25-P75 zone, capacity bar for reservoirs, weather card (temp/wind+Beaufort/AQI/UV/humidity/sunrise/sunset — fetched separately with its own loading spinner), 7-day forecast, station metadata, data source label, manual refresh button. Works as modal overlay (in-app) or full page (direct URL) |
| `/login` | Built | Email/username + password form, error display, loading state, redirects authenticated users to dashboard |
| `/register` | Built | Username, email, password with confirm, client-side validation (8 char min, match check), redirects authenticated users to dashboard |
| `/map` | Built | Interactive MapLibre GL JS map (CartoDB Voyager tiles). Below zoom 6: a province overlay with per-province fills (unique colours), borders, labels, and a single per-province cluster marker sized by total reading count from `/api/stations/provinces`. Above zoom 6: per-station markers colour-coded by rating, with native clustering. Basemap city/town labels render above station dots (via `beforeId`). Click-to-zoom clusters, multi-station selection with aggregated summary panel (avg flow/level/temp, highs/lows, dominant rating, sunrise/sunset, nearby stations), "Save as Collection" link from the panel, `?collection={id}` deep-link consumer (pre-selects stations + fits bounds), province/type/showNoData filters, rating legend, URL state sync, sessionStorage persistence |
| `/collections` | Built | Auth-required list with Mine / Shared with me / Favourited tabs. Guests see the page but each tab shows a sign-up CTA. Header has Discover and "+ New collection" buttons. |
| `/collections/new` | Built | Create form. Reads `?stations=…&name=…` for prefill (used by the map's "Save as Collection" button). |
| `/collections/[id]` | Built | Read-only detail with aggregation panels, station list, collaborators (visible to viewer/editor/owner), share link (owner-only). Action buttons: Favourite (auth), View on Map (when stations exist), Edit (owner+editor), Feature/Unfeature (admin-only). |
| `/collections/[id]/edit` | Built | Owner+editor editor. Sections: Details, Stations (existing list with remove + StationPicker), Collaborators (owner-only), Share link (owner-only), Danger zone (owner-only delete). |
| `/collections/discover` | Built | Public browse with search, province dropdown, popular-tag chips, Featured toggle. URL state synced. |
| `/collections/share/[token]` | Built | Anonymous-friendly read-only viewer. Falls back to "Link expired" on 404. |
| `/advanced-data` | Not started | Historical data explorer |
| `/about` | Not started | |
| `/contact` | Not started | |

## Error Handling

### Global Error Boundary (`error.js`)

If any component throws an unhandled error, Next.js catches it and renders the error boundary instead of a white screen. Shows the WaterPulse logo, the error message, a "Try Again" button (resets the error boundary), and a link to the dashboard.

### 404 Page (`not-found.js`)

Custom 404 page matching the landing page's dark navy hero style. Shows a "Page not found" message with links to the dashboard and home page.

### Dashboard Error States

The dashboard tracks three independent error states:

- **Province loading failure** — red banner with retry button above the province picker
- **Station loading failure** — centred error message with retry button replacing the station grid
- **Refresh failure** — inline red banner below the controls row

All errors clear automatically when the next attempt starts.

### Auth Page Redirects

Login and register pages check `isAuthenticated` on mount. If the user already has a valid session, they are redirected to `/dashboard` via `router.replace()` (no history entry). Pages return `null` during the auth check to prevent form flash.

## Dashboard Features

### Province Picker

Buttons for each province, sorted alphabetically by province code. Each button shows the province code and total station count. The selected province is highlighted in blue.

### Province Header

Shows the province name with a breakdown of active stations: "{X} River and {Y} Lake/Reservoir Stations Active". Also shows the last updated timestamp, derived from the most recent `fetched_at` across loaded station readings (not from a separate API call).

### Province-Scoped Search

The search bar sends queries to `GET /api/stations/search?q=X&province=Y&limit=200`, scoping results to the currently selected province. Search is debounced at 300ms. The search re-runs automatically if the province changes while a search query is active.

### Station Type Filter

Filter buttons for All, River, and Lake/Reservoir (meteorological stations excluded). Each shows a count badge. The counts reflect the total stations (including inactive), while the grid only shows stations matching the current filter AND the `showNoData` toggle.

### Show Inactive Stations Toggle

A toggle button that shows/hides stations without current reading data. Default is off (inactive stations hidden). Shows a badge with the count of hidden stations. State persists in Zustand across navigation.

### Infinite Scroll

The dashboard renders station cards in batches of 15 to avoid loading hundreds of cards at once. All station data is fetched upfront from the API (per-province datasets are small enough), but rendering is controlled by a `displayCount` state variable that starts at 15 and grows as the user scrolls.

**How it works:**
1. An `IntersectionObserver` watches a sentinel `<div>` placed below the station grid
2. When the sentinel enters the viewport (or comes within 200px via `rootMargin: "200px"`), `displayCount` increments by 15
3. The grid renders `filteredStations.slice(0, displayCount)` — only the first `displayCount` cards
4. A "Showing X active stations of Y total" counter appears above the grid (or "Showing all Y stations" when inactive stations are toggled on)
5. A loading spinner shows below the grid while more cards are available
6. The sentinel is hidden once all cards are rendered, so the observer stops firing

**Reset behaviour:** `displayCount` resets to 15 whenever the user switches province, changes the type filter, toggles the "Show Inactive Stations" button, or gets new search results. This ensures each view always starts with the first batch of 15.

**Performance:** All derived station lists and counts (`filteredStations`, `typeCounts`, `activeRiverCount`, etc.) are wrapped in `useMemo` so they only recalculate when their dependencies change, not on every render.

### Data Freshness

The backend scheduler refreshes readings every 10 minutes automatically. The frontend does not auto-refresh — users can trigger a manual refresh via the refresh button on the dashboard or station detail page.

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

## Docker

### Dockerfile (Multi-Stage Build)

The frontend Dockerfile (`waterpulse-frontend/Dockerfile`) uses a three-stage build to keep the production image small:

| Stage | Base Image | Purpose |
|-------|-----------|---------|
| **deps** | `node:22-alpine` | Installs npm dependencies (`npm ci`) — cached unless package*.json changes |
| **builder** | `node:22-alpine` | Copies source code and runs `npm run build` with the standalone output mode |
| **runner** | `node:22-alpine` | Copies only the standalone server.js and static assets — final image ~100 MB |

Without the multi-stage build, the image would be ~500 MB because it would include the full `node_modules/` directory.

### next.config.mjs

`output: "standalone"` was added to `next.config.mjs` to enable Next.js standalone builds. This produces a self-contained `server.js` in `.next/standalone/` that includes only the node_modules packages actually needed at runtime. This is required for the Docker production build.

### .dockerignore

The `.dockerignore` file excludes `node_modules/` (~300 MB) and `.next/` from the Docker build context. Without this, Docker would copy these directories into the build context (making builds slow), only for them to be recreated inside the container by `npm ci` and `npm run build`.

## Rules
- All backend calls go through `src/lib/api.js` — never use raw `fetch()` or bare `axios`
- NEVER store tokens in `localStorage` or `sessionStorage`
- Use Canadian English: favourites, colours, metres
- `.env.local` contains `NEXT_PUBLIC_API_URL` — never commit it
- State that must survive navigation goes in Zustand stores (`src/stores/`), not `useState`
