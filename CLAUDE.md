# WaterPulse Canada

Real-time river, lake, and reservoir conditions for anyone visiting Canada's waterways. Recreational users (anglers, kayakers, rafters, swimmers) and professionals (fire services, river rescue, field workers, municipal staff).

## Repo Layout
- `waterpulse-frontend/` — Next.js (App Router), JavaScript, Tailwind CSS
- `waterpulse-backend/` — FastAPI, Python 3.12, async SQLAlchemy, PostgreSQL
- `nginx/` — Reverse proxy config for Docker
- `docker-compose.yml` — Container orchestration (db, backend, frontend, nginx)

The frontend runs on port 3000, the backend on port 8000, Nginx on port 80.

## How They Connect
- Frontend calls the backend REST API at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- Auth uses HTTPOnly cookies — the backend sets them, the browser sends them, the frontend never touches the JWT
- CSRF protection: backend sets a readable `csrf_token` cookie; frontend echoes it as `X-CSRF-Token` header on POST/PUT/DELETE
- CORS: backend must use `allow_credentials=True` with an explicit origin list (never wildcard `*`)

## Auth Flow (Shared Contract)
1. User submits credentials → frontend calls `POST /api/auth/login`
2. Backend validates, creates JWT, responds with two `Set-Cookie` headers:
   - `access_token` — HTTPOnly, Secure, SameSite=Lax (the JWT, invisible to JS)
   - `csrf_token` — plain cookie (readable by JS for CSRF header)
3. Frontend calls `GET /api/auth/me` → backend reads cookie, returns user object
4. All subsequent fetches include `credentials: "include"` — browser attaches cookies automatically
5. Logout: `POST /api/auth/logout` → backend clears both cookies
6. Guest users browse freely; accounts are needed for server-side favourites
7. Guest favourites use a separate non-HTTPOnly cookie (not the auth token)

## Data Model Overview
- ~8,500 total monitoring stations across 13 provinces and territories; active count varies seasonally
- Primary source: ECCC (Environment and Climate Change Canada) — all of Canada
- Supplementary source: Alberta provincial API (rivers.alberta.ca) — enriches shared stations, adds provincial-only stations
- Station types: R (river), L (lake/reservoir), M (meteorological) — only R and L are shown in user-facing endpoints and the frontend
- Readings refresh every 10 minutes via backend scheduler, plus on-demand via frontend or admin endpoints
- Historical sync runs annually on January 1st at 03:00 UTC via backend scheduler, plus on-demand via admin endpoint
- Ratings are percentile-based against historical norms (±7 day window, up to 5 years of data)
- Weather and AQI from Open-Meteo (no API key needed), fetched by the backend
- All timestamps stored as naive UTC — providers convert local times before storing

## Docker
- `docker-compose up --build` — starts all 4 services (db, backend, frontend, nginx)
- Copy `.env.example` to `.env` and fill in secrets before first run
- Database data persists in the `pgdata` named volume
- Backend runs Alembic migrations automatically on startup via `entrypoint.sh`
- Frontend uses `output: "standalone"` for optimised Docker builds
- `NEXT_PUBLIC_API_URL` is a build-time arg (baked into JS at build)

## Important Rules (Both Sides)
- NEVER store auth tokens in localStorage or sessionStorage
- NEVER hardcode station counts — fetch from the API, fall back gracefully
- Use Canadian English: favourites, colours, metres
- `.env` and `.env.local` files are never committed
