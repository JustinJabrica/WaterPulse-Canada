# WaterPulse Security Audit — SEC-AUDIT-2026.1: Known Vulnerabilities in the Stack + Latest-Version Upgrade

**Status:** completed · **Run date:** 2026-11-20 · **Branch:** `security/audit-2026.1` · **Author:** WaterPulse engineering

> Scope: every known, published vulnerability affecting the technology this project ships —
> npm and PyPI dependencies (direct and transitive), runtime and base images, reverse proxy,
> database and Kubernetes ingress — plus the configuration weaknesses found while checking whether
> each advisory is reachable. Every component was then moved to its latest available version
> wherever possible. References are IEEE-numbered (§10).

## 1. Summary

| Area | Before | After |
|---|---|---|
| Frontend (`npm audit`) | **23 packages, 100 distinct advisories** — 6 critical, 49 high, 40 moderate, 5 low | **0** |
| Backend (OSV, built image `pip freeze`) | **8 packages, 25 distinct advisories** (44 OSV records incl. PYSEC aliases) — 2 critical, 12 high, 6 moderate, 4 low, 1 unrated | **0** |
| Reverse proxy | Caddy 2.11.4 (floating `2-alpine` tag, 5 months stale) — CVE-2026-55458 | Caddy 2.11.9 (pinned) |
| k8s ingress | ingress-nginx — **retired Mar 2026, no security fixes**; installed from unpinned `main` | Envoy Gateway v1.10.0 (Gateway API, pinned Helm chart) |
| Runtimes | Python 3.12.15 · Node 22.23.3 · PostgreSQL 16.15 | Python 3.15.2 · Node 26.13.1 (Active LTS) · PostgreSQL 19.0 |
| Config | 1 critical, 2 high, 4 medium findings (§4) | All fixed; 2 residual items documented (§8) |

The most serious problem found was **not a library CVE**: the deployed `SECRET_KEY` was the
public placeholder from `.env.example`, which made every JWT forgeable (C-1). At the time of the
audit the `users` table held 0 rows, so no account was exposed; the key was rotated and the backend
now refuses to start with a placeholder or short key.

## 2. Scope & method

- **npm:** `npm audit` (GitHub Advisory Database) on the committed lockfile before and after;
  `npm audit --package-lock-only` re-run against the pre-audit lockfile (`e9f681c`) for the
  exact "before" list in Appendix A.
- **Python:** `pip freeze` from the *built* backend image (what actually ships, including
  transitive packages), queried against the OSV database [1] via `/v1/querybatch`; repeated on the
  rebuilt image. Python 3.15 viability tested with `pip install --dry-run --only-binary=:all:` in
  `python:3.15.x-slim` (every compiled dependency has a cp315 wheel) and on Windows/Python 3.14
  for bare-metal development.
- **Images & services:** latest tags from Docker Hub; Caddy checked against OSV (Go ecosystem);
  ingress-nginx lifecycle from the Kubernetes project [2].
- **Supply chain:** lockfile history and `node_modules`/npm-cache inspection for the March 2026
  axios compromise [3].
- **Reachability:** for each advisory, whether the vulnerable code path is used by this app
  (grep of the source, runtime probes through Caddy).
- **Verification:** full compose stack rebuilt and exercised end-to-end (§7).

## 3. Dependency findings and applicability

Full advisory lists are in Appendices A (npm) and B (PyPI). This table covers the ones that
drove decisions. "Reachable" means: can the vulnerable code be triggered in *this* app as
deployed?

| ID | Component (before → after) | Advisory | Sev. | Reachable here? | Status |
|---|---|---|---|---|---|
| D-1 | next 16.2.4 → **16.4.6** | GHSA-p293-qw3h-jr36 — unauthenticated RCE on **Windows-hosted** servers | Critical | **Yes, in development** — `next dev`/`next start` run on this Windows machine; containers are Linux | Fixed |
| D-2 | next | GHSA-2xp9-vwfh-vxw4 / GHSA-2464-fhr4-w9xw — RCE in Image Optimization (AVIF/SVG); GHSA-cjq9-62q9-8jv4 — SSRF | Critical/High | **Limited** — app doesn't use `next/image`, but `/_next/image` is live by default. Probe: SVG → 400 "type not allowed", remote URL → 400 "not allowed"; `public/` has no raster images | Fixed |
| D-3 | next | GHSA-673q-mjm6-r5xr (`use cache` RCE), GHSA-vcvr-r3jv-pc5j (`next/og` RCE), Server Actions DoS/SSRF, Middleware/Proxy bypasses | Critical/High | **No** — no `use cache`, `next/og`, `"use server"` or middleware/proxy file in `src/` | Fixed |
| D-4 | next | Cache poisoning of SSG/ISR pages (GHSA-4jqv-mc3x-m676, GHSA-mcj8-r9mp-w47p), RSC DoS (GHSA-8h8q-6873-q5fj), XSS (GHSA-ffhc-5mcf-pf4q, GHSA-gx5p-jg67-6x7h) | High/Mod. | **Yes** — self-hosted App Router with static pages | Fixed |
| D-5 | maplibre-gl 5.24.0 → **6.19.0** (major) | GHSA-jrc7-96c5-q579 — XSS sanitizer bypass in `DOM.sanitize()` | Critical | **Low** — popups are React children, not `setHTML`; attribution comes from our own styles. Fix exists only in 6.x | Fixed (code change: ESM namespace import + `setWorkerUrl`, §6) |
| D-6 | axios 1.15.2 → **1.21.1** | 28 advisories (ReDoS, proxy-credential leaks, prototype-pollution gadgets, HTTP/2 bypasses) | High | **Low** — browser-only use; most target the Node HTTP/HTTP2 adapters or need a separate prototype-pollution bug | Fixed |
| D-7 | postcss, sharp (via next), browserslist, brace-expansion, js-yaml, nanoid, zod, follow-redirects, form-data, source-map-js, … | 33 build-time/transitive advisories | High/Mod. | Mostly build-time. `sharp` (libvips/libheif/librsvg CVEs) backs the image optimizer, see D-2 | Fixed (next 16.4.6 pins patched postcss 8.5.23 / sharp 0.35.5; `npm audit fix`) |
| D-8 | `navigator` 1.0.1 | — (no advisory) | — | Unused 2012 Node shim, never imported; pure supply-chain surface | **Removed** |
| D-9 | python-jose 3.3.0 → **PyJWT 2.15.1** | GHSA-6c5p-j8vq-pqhj / GHSA-3qf3-8w2g-rqmx — algorithm confusion (CVE-2024-33663; **DER-key variant unfixed upstream**) | Critical | **Low as a library bug** — HMAC-only with an `algorithms=[…]` allow-list. But see C-1: the key itself was public | Replaced |
| D-10 | python-jose | GHSA-cjwg-qfpm-7377 — JWE decompression DoS (CVE-2024-33664); PYSEC-2025-185 (CVE-2024-29370) | Mod. | No — app never decodes JWE | Replaced |
| D-11 | ecdsa 0.19.2 (via jose) | GHSA-wj6h-64fc-37mp — Minerva timing attack (CVE-2024-23342), **no fix** | High | No — no ECDSA signing | Removed with jose |
| D-12 | pyasn1 0.6.4 (via jose→rsa) | 4 × quadratic-time DoS (CVE-2026-119194…119197) | High | No — not on a request path | Removed with jose |
| D-13 | starlette 0.41.3 → **1.10.0** | GHSA-86qp-5c8j-p5mr — Host header poisons `request.url.path` (CVE-2026-48710) | Mod. | **Partly** — `CSRFMiddleware` decides on `request.url.path`; a cross-site browser cannot set Host, so practical CSRF impact is low | Fixed |
| D-14 | starlette | Range-header DoS, form-limit DoS, StaticFiles UNC SSRF, `HTTPEndpoint` getattr, multipart DoS, url.hostname poisoning (6 more) | High/Mod./Low | No — no `FileResponse`, `request.form()`, `StaticFiles` or `HTTPEndpoint` | Fixed |
| D-15 | python-multipart 0.0.20 → **0.0.34** | 7 advisories incl. GHSA-wp53-j4wj-2cfg arbitrary file write (non-default config), header/preamble DoS | High | No — no `Form`/`UploadFile` endpoints | Fixed |
| D-16 | python-dotenv 1.0.1 → **1.2.4** | GHSA-mf9w-mj56-hr94 — symlink overwrite in `set_key` | Mod. | No — `set_key` not called | Fixed |
| D-17 | dnspython 2.9.0 → **2.9.2** (via email-validator) | GHSA-vvf4-9x63-8xvv — resource exhaustion | High | No — deliverability (DNS) checks are off | Fixed |
| D-18 | Caddy 2.11.4 → **2.11.9** | GHSA-8qx7-j2v2-x6q5 — hop-by-hop headers leak through `reverse_proxy` (CVE-2026-55458) | — | **Yes** — Caddy reverse-proxies every request | Fixed (exact tag pinned) |
| D-19 | ingress-nginx (k8s) | Project retired (no further releases or security fixes) [2]; installed from unpinned `main` | High | k8s path only | **Replaced** by Envoy Gateway v1.10.0 [4] |

## 4. Configuration and application findings

| ID | Finding | Sev. | Fix |
|---|---|---|---|
| C-1 | `.env` `SECRET_KEY` equal to the committed `.env.example` placeholder, so anyone could forge an access token for any user id. `docs/cloudflare-tunnel.md` describes exposing the stack publicly. The bare-metal `waterpulse-backend/.env` also used a placeholder. | **Critical** | Both keys rotated (`token_urlsafe(64)`). `config.py` validator refuses startup if `SECRET_KEY` is a known placeholder or < 32 chars, and if `ALGORITHM` ∉ {HS256, HS384, HS512}. |
| C-2 | `POST /api/admin/sync-stations`, `sync-historical`, `refresh-readings` had **no authentication** (only 5/min) and were CSRF-exempt: anyone could trigger Canada-wide upstream fetches, abusing provider APIs and risking IP bans. | **High** | New `require_admin` dependency: superuser session (CSRF enforced) **or** `Authorization: Bearer ADMIN_API_TOKEN` (constant-time compare; disabled when unset). `/api/admin/` removed from CSRF exemptions. `GET /api/admin/status` stays public for the home page. |
| C-3 | `POST /api/readings/refresh` was public with no rate limit; with no filter it refreshed every station in Canada. | Medium | 20/min per client; ≤ 50 `station_numbers`; a no-filter refresh is admin-only. UI callers unaffected. |
| C-4 | slowapi keyed on `request.client.host`, which is **Caddy's IP**: register (3/h) and login (10/min) limits were one global bucket, so one client could lock everyone out. | Medium | uvicorn `--proxy-headers --forwarded-allow-ips` (Caddy discards client-sent `X-Forwarded-For`). **Residual behind Cloudflare tunnels** (§8). |
| C-5 | Postgres 5432 and backend 8000 published on all host interfaces (LAN-reachable). | Medium | Bound to `127.0.0.1`, host ports configurable (`POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`). |
| C-6 | Backend and frontend containers ran as root. | Medium | Backend uid 10001 `app`; frontend `node` (uid 1000). |
| C-7 | Floating image tags (`caddy:2-alpine`, `postgres:16-alpine`, `node:22-alpine`, `python:3.12-slim`) silently went stale. | Medium | Exact tags pinned + Dependabot for npm, pip, Docker, compose and k8s (`.github/dependabot.yml`). |
| C-8 | A token without `sub` raised an unhandled `TypeError` (500). | Low | PyJWT `options={"require": ["exp","sub"]}`, broader exception handling → 401. |
| C-9 | CSRF double-submit compared tokens with `!=` (not constant-time). | Low | `secrets.compare_digest`. |
| C-10 | `POSTGRES_PASSWORD` was 8 characters while the port was LAN-exposed. | Low | Rotated to a 43-character value when PG19 initialised. |
| C-11 | `Limiter(default_limits=["60/minute"])` is **not enforced** on undecorated endpoints (slowapi needs `SlowAPIMiddleware`, which isn't installed); the README claimed it was. | Low | Docs corrected; enabling a global limit is a follow-up (§8). |
| C-12 | Healthchecks were broken. Backend: `curl` is absent from `python:*-slim`. Frontend: `localhost` resolves to `::1` but Next listens on IPv4. | Low (ops) | Backend probes with Python; frontend probes `127.0.0.1` with `HOSTNAME=0.0.0.0`. Both report `healthy`. |

## 5. Checked — not affected

- **axios npm account takeover (2026-03-31)** [3]. The malicious `axios@1.14.1` / `0.30.4` added
  `plain-crypto-js@4.2.1`, whose postinstall dropped a RAT. Evidence this project was not hit:
  - lockfile history (`git log -- waterpulse-frontend/package-lock.json`) shows axios 1.14.0 →
    1.15.0 → 1.15.2, never 1.14.1
  - no `plain-crypto-js` in `node_modules`
  - no `plain-crypto-js` entry in the npm cache index (`%LOCALAPPDATA%/npm-cache/_cacache/index-v5`)
- **Next.js RCE paths that need app features this project doesn't use** (D-3) were patched anyway.

## 6. Upgrades performed and breaking changes handled

| Change | Breaking change and how it was handled |
|---|---|
| maplibre-gl 5 → 6 [5] | ESM-only with no default export → `import * as maplibregl`; `mapLib={maplibregl}` passed to react-map-gl. **The worker failed to load**: v6 derives its URL from `import.meta.url`, which Turbopack rewrites, so it resolved to the page itself. Fixed with `setWorkerUrl(new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).href)`, which Turbopack emits as a hashed static asset. |
| python-jose → PyJWT | API swap in `app/auth.py`. HS256 tokens are format-compatible; sessions were invalidated anyway by the C-1 key rotation. |
| FastAPI 0.115 → 0.165 / Starlette 0.41 → 1.10 [6] | 1.0 removed `on_event`, decorator routes and similar; the app already used `lifespan` and `include_router`. `BaseHTTPMiddleware` remains. No code changes needed. |
| SQLAlchemy 2.0 → 2.1 [7] | greenlet is now opt-in → `sqlalchemy[asyncio]`. No `filter_by` usage (new ambiguity errors don't apply). |
| uvicorn `[standard]` | Expanded to explicit `uvloop`/`httptools`/`watchfiles`, because the extra pulls PyYAML, which has no cp315 wheel. uvloop carries uvicorn's own `sys_platform != "win32"` marker so Windows dev still installs. |
| pydantic-settings | `class Config` (deprecated, removed in v3) → `SettingsConfigDict`. |
| PostgreSQL 16 → 19 [8] | 18+ images keep data in `/var/lib/postgresql/<major>/docker` and expect the volume at `/var/lib/postgresql`. Migration: `pg_dump -Fc` inside the PG16 container → `docker cp` (sha256 verified, `pg_restore -l` gate) → new `pgdata19` volume → `pg_restore`. **Row counts identical in all 12 tables** (incl. 5,409,112 `historical_daily_means`). PG16 volume kept for rollback. |
| ingress-nginx → Envoy Gateway | `k8s/gateway.yaml`: GatewayClass, EnvoyProxy (NodePort 30080 for kind), Gateway and HTTPRoute (1800 s timeout for long syncs). `kind-cluster.yaml` pins `kindest/node:v1.37.0@sha256:a1ed56cf…`. |

## 7. Verification evidence

| Check | Result |
|---|---|
| `npm audit` (frontend) | `found 0 vulnerabilities` |
| OSV on rebuilt backend image (41 packages) | 0 advisories; `python-jose`, `ecdsa`, `rsa`, `pyasn1` absent |
| `next build` (16.4.6, Turbopack, Node 26) | Compiles; 18 routes generated |
| `docker build` backend / frontend | OK on `python:3.15.2-slim` / `node:26.13.1-alpine`, no compiler needed |
| Containers | backend `uid=10001(app)`, frontend `uid=1000(node)`; db, backend and frontend `healthy` |
| PG19 | `alembic upgrade head` no-op on restored data; scheduler started |
| Security headers (via Caddy) | `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` present; `Server` stripped |
| Auth | register 201 → `/api/auth/me` 200; token without `sub` → 401; token signed with the old placeholder key → 401; `alg=none` token → 401 |
| CSRF | logout with no / wrong header → 403; matching header → 200 |
| Admin | guest → 401; logged-in non-admin → 403; wrong bearer → 401; correct bearer → 200 (PE province refresh) |
| Public refresh | no filter → 400; 51 stations → 422; 21st call within a minute → 429 |
| Client-IP keying | uvicorn logs show the client (`172.18.0.1`), not Caddy (`172.18.0.5`) |
| `/map` in headless Chromium (Edge 157, WebGL2) | Basemap, province overlay and station clusters render; no worker or console errors besides the expected guest 401 on `/api/auth/me` |
| k8s manifests | `kubeconform -strict`: 14 resources valid (Gateway API + EnvoyProxy CRD schemas). `envoyService.type/patch` confirmed in the v1.10.0 CRD. **Not run on a live kind cluster** (kind/helm not installed). |
| `dependabot.yml` | Valid against the published schema |

## 8. Not upgraded to the absolute latest, and why

| Component | Kept at | Reason |
|---|---|---|
| ESLint | 9.39.5 (maintenance line) | `eslint-plugin-react` 7.37.5, `eslint-plugin-import` 2.32.0 and `eslint-plugin-jsx-a11y` 6.10.2 (all via `eslint-config-next` 16.4.6) declare peer support only up to ESLint 9. Dependabot ignores ESLint majors until they catch up. |
| httpx | 0.28.1 | Already the latest release. |
| psycopg2-binary | 2.9.13 | Latest of its line. SQLAlchemy 2.1 now defaults to psycopg 3; switching is optional (follow-up). |
| @protomaps/basemaps, babel-plugin-react-compiler, bcrypt | 5.7.2, 1.0.0, 5.0.0 | Already latest. |

## 9. Residual risk and follow-ups

1. **Tunnel client IPs.** Behind a Cloudflare quick tunnel every visitor reaches Caddy from the
   same peer, so per-IP limits are shared. Fix when needed: Caddy
   `servers { trusted_proxies …; client_ip_headers CF-Connecting-IP X-Forwarded-For }`,
   enabled only for tunnel mode. Documented in `docs/cloudflare-tunnel.md`.
2. **Content-Security-Policy.** Not yet set; needs MapLibre `worker-src` and the tile/glyph hosts
   allow-listed and tested.
3. **Global rate limit.** Install `SlowAPIMiddleware` with a generous default once normal
   page-load request volumes are measured (C-11).
4. **Image optimizer.** The app doesn't use `next/image`; `images: { unoptimized: true }` would
   remove the `/_next/image` surface entirely (D-2).
5. **Sessions during past public exposure.** Treat any session issued while the placeholder key
   was live as untrusted. At audit time there were 0 users, and rotation invalidated all tokens.
6. **slowapi** calls `asyncio.iscoroutinefunction`, which is removed in Python 3.16. Watch for a
   slowapi release before moving to 3.16.
7. **Pre-existing lint errors.** 28 problems (23 errors, 5 warnings: `react-hooks/set-state-in-effect` and others). Same
   plugin version before and after the upgrade, so they are not regressions. Not security-relevant.
8. **Cleanup after sign-off.** Delete the PG16 rollback volume (`docker volume rm
   waterpulse-canada_pgdata`) and `backups/` (the dump contains password hashes).
9. **GitHub settings (manual).** Enable Dependabot alerts and security updates.
10. **k8s.** Run the Envoy Gateway path once on a live kind cluster.
11. **Partial map check.** Station popups and click interactions on `/map` were not exercised by
    the headless check; only rendering was.

## 10. References (IEEE)

[1] Open Source Vulnerabilities, "OSV API — querybatch," Google/OpenSSF, 2026. [Online]. Available: https://google.github.io/osv.dev/post-v1-querybatch/. [Accessed: Nov. 20, 2026].
[2] Kubernetes SIG Network and Security Response Committee, "Ingress NGINX retirement: what you need to know," Kubernetes Blog, Nov. 11, 2025. [Online]. Available: https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/. [Accessed: Nov. 20, 2026].
[3] Chainguard, "Malicious axios versions published to npm," Chainguard Unchained, Mar. 2026. [Online]. Available: https://www.chainguard.dev/unchained/malicious-axios-versions-published-to-npm-chainguard-customers-protected. [Accessed: Nov. 20, 2026].
[4] Envoy Gateway, "Install with Helm" and "Customize EnvoyProxy," v1.10 documentation, 2026. [Online]. Available: https://gateway.envoyproxy.io/docs/install/install-helm/. [Accessed: Nov. 20, 2026].
[5] MapLibre, "v5 to v6 migration guide," MapLibre GL JS documentation, 2026. [Online]. Available: https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/. [Accessed: Nov. 20, 2026].
[6] Encode/Kludex, "Starlette release notes (1.0.0–1.10.0)," 2026. [Online]. Available: https://github.com/Kludex/starlette/blob/main/docs/release-notes.md. [Accessed: Nov. 20, 2026].
[7] SQLAlchemy, "What's new in SQLAlchemy 2.1," 2026. [Online]. Available: https://docs.sqlalchemy.org/en/21/changelog/migration_21.html. [Accessed: Nov. 20, 2026].
[8] Docker Official Images, "postgres: change PGDATA to a version-specific directory (PR #1259)," GitHub, 2025. [Online]. Available: https://github.com/docker-library/postgres/pull/1259. [Accessed: Nov. 20, 2026].
[9] GitHub, "Dependabot options reference," GitHub Docs, 2026. [Online]. Available: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference. [Accessed: Nov. 20, 2026].
[10] Node.js, "Evolving the Node.js release schedule," Node.js Blog, 2026. [Online]. Available: https://nodejs.org/en/blog/announcements/evolving-the-nodejs-release-schedule. [Accessed: Nov. 20, 2026].

## 11. How to reproduce

```bash
# Frontend advisories
cd waterpulse-frontend && npm audit
# Backend advisories: freeze the shipped image, then query OSV (api.osv.dev/v1/querybatch)
docker run --rm --entrypoint pip waterpulse-canada-backend:latest freeze
# Runtime checks (stack up; ADMIN_API_TOKEN from .env)
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost/api/admin/sync-stations   # 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost/api/readings/refresh      # 400
# k8s manifests
docker run --rm -v "$PWD/k8s:/k8s:ro" ghcr.io/yannh/kubeconform:latest -strict -summary \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  -ignore-filename-pattern kind-cluster /k8s/
```

---

## Appendix A — Frontend advisories before the upgrade (`npm audit`, lockfile `e9f681c`)

All 100 resolved by the upgrade (`npm audit` → 0).

| Package | Severity | Affected range | Advisory | Title |
|---|---|---|---|---|
| @babel/core | low | `<=7.29.0` | [GHSA-4x5r-pxfx-6jf8](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8) | @babel/core: Arbitrary File Read via sourceMappingURL Comment |
| axios | high | `>=1.0.0 <1.16.0` | [GHSA-hfxv-24rg-xrqf](https://github.com/advisories/GHSA-hfxv-24rg-xrqf) | Axios: Regular Expression Denial of Service (ReDoS) via Cookie Name Injection |
| axios | high | `>=1.7.0 <1.16.0` | [GHSA-777c-7fjr-54vf](https://github.com/advisories/GHSA-777c-7fjr-54vf) | Allocation of Resources Without Limits or Throttling in Axios |
| axios | high | `>=1.0.0 <1.16.0` | [GHSA-p92q-9vqr-4j8v](https://github.com/advisories/GHSA-p92q-9vqr-4j8v) | Axios: Proxy-Authorization Credential Leak to Origin Server Across HTTP-to-HTTPS Redirect in Axios Node.js HTTP Adapter |
| axios | high | `>=1.0.0 <1.16.0` | [GHSA-j5f8-grm9-p9fc](https://github.com/advisories/GHSA-j5f8-grm9-p9fc) | Axios: Proxy-Authorization header leaks to redirect target when proxy is re-evaluated to direct connection |
| axios | high | `>=1.0.0 <1.16.0` | [GHSA-35jp-ww65-95wh](https://github.com/advisories/GHSA-35jp-ww65-95wh) | axios Vulnerable to Full Man-in-the-Middle via Prototype Pollution Gadget in `config.proxy` |
| axios | high | `>=1.15.0 <1.16.0` | [GHSA-pjwm-pj3p-43mv](https://github.com/advisories/GHSA-pjwm-pj3p-43mv) | axios's shouldBypassProxy does not recognize IPv4-mapped IPv6 addresses, allowing NO_PROXY bypass (incomplete fix for CVE-2025-62718) |
| axios | high | `>=1.15.2 <1.18.0` | [GHSA-gcfj-64vw-6mp9](https://github.com/advisories/GHSA-gcfj-64vw-6mp9) | Axios Node HTTP adapter can use an inherited proxy after interceptor config cloning |
| axios | high | `>=1.15.0 <1.20.0` | [GHSA-mghh-pgcx-3jjj](https://github.com/advisories/GHSA-mghh-pgcx-3jjj) | Axios: ReDoS (O(N²)) in shouldBypassProxy host normalization, reachable via untrusted redirect Location |
| axios | high | `>=1.15.1 <1.20.0` | [GHSA-x97p-jq2g-jp4f](https://github.com/advisories/GHSA-x97p-jq2g-jp4f) | Axios: Prototype Pollution Gadget in axios toFormData Options |
| axios | high | `>=1.13.0 <1.20.0` | [GHSA-3pq3-5fj3-cg6v](https://github.com/advisories/GHSA-3pq3-5fj3-cg6v) | Axios: HTTP/2 adapter bypasses configured DNS lookup and proxy controls |
| axios | high | `>=1.13.0 <1.20.0` | [GHSA-542g-h47m-68v8](https://github.com/advisories/GHSA-542g-h47m-68v8) | Axios: Denial of Service via Unhandled 'error' Event in HTTP/2 ClientHttp2Session Initialization |
| axios | high | `>=1.15.2 <1.20.0` | [GHSA-m8m8-qj5v-23w3](https://github.com/advisories/GHSA-m8m8-qj5v-23w3) | Axios: Node HTTP adapter prototype-pollution gadget allows request socket hijack via inherited createConnection |
| axios | moderate | `>=1.0.0 <1.16.0` | [GHSA-898c-q2cr-xwhg](https://github.com/advisories/GHSA-898c-q2cr-xwhg) | axios has DoS & Header Injection via Prototype Pollution Read-Side Gadgets in axios merge functions |
| axios | moderate | `>=1.15.2 <1.18.0` | [GHSA-xj6q-8x83-jv6g](https://github.com/advisories/GHSA-xj6q-8x83-jv6g) | Axios: Prototype pollution auth subfields can inject Basic auth |
| axios | moderate | `>=1.0.0 <1.18.0` | [GHSA-mmx7-hfxf-jppx](https://github.com/advisories/GHSA-mmx7-hfxf-jppx) | Axios: Prototype pollution gadgets can alter axios request construction |
| axios | moderate | `>=1.0.0 <1.18.0` | [GHSA-pmv8-rq9r-6j72](https://github.com/advisories/GHSA-pmv8-rq9r-6j72) | Axios: Deep formToJSON Key Recursion Can Cause Denial of Service |
| axios | moderate | `>=1.13.0 <1.18.0` | [GHSA-mwf2-3pr3-8698](https://github.com/advisories/GHSA-mwf2-3pr3-8698) | Axios: HTTP/2 streamed uploads bypass `maxBodyLength` |
| axios | moderate | `>=1.0.0 <1.18.0` | [GHSA-7q8q-rj6j-mhjq](https://github.com/advisories/GHSA-7q8q-rj6j-mhjq) | Axios: Nested axios option objects can consume polluted prototype values |
| axios | moderate | `>=1.7.0 <1.18.0` | [GHSA-jqh4-m9w3-8hp9](https://github.com/advisories/GHSA-jqh4-m9w3-8hp9) | Axios: Fetch adapter `ReadableStream` uploads bypass `maxBodyLength` |
| axios | moderate | `>=1.15.0 <1.18.0` | [GHSA-f4gw-2p7v-4548](https://github.com/advisories/GHSA-f4gw-2p7v-4548) | Axios: NO_PROXY bypass for 0.0.0.0 local addresses in axios |
| axios | moderate | `>=1.0.0 <1.18.0` | [GHSA-42h9-826w-cgv3](https://github.com/advisories/GHSA-42h9-826w-cgv3) | Axios: Excessive recursion in formDataToJSON can cause denial of service |
| axios | moderate | `>=1.15.1 <1.18.0` | [GHSA-hcpx-6fm6-wx23](https://github.com/advisories/GHSA-hcpx-6fm6-wx23) | Axios form serializer maxDepth bypass via {} metatoken |
| axios | moderate | `>=1.7.0 <1.20.0` | [GHSA-vh66-26gq-q6x8](https://github.com/advisories/GHSA-vh66-26gq-q6x8) | Axios: Prototype pollution gadget in fetch adapter can alter outbound requests |
| axios | moderate | `>=1.0.0 <1.20.0` | [GHSA-9fr6-4gfg-395g](https://github.com/advisories/GHSA-9fr6-4gfg-395g) | Axios: Prototype-Pollution Gadget in the Default Instance Allows Inherited Object.prototype.method to Override HTTP Method |
| axios | moderate | `>=1.0.0 <1.20.0` | [GHSA-j8rh-479h-cp32](https://github.com/advisories/GHSA-j8rh-479h-cp32) | Axios: Header Injection via Inherited headers After Minimal Interceptor |
| axios | moderate | `>=1.12.0 <1.20.0` | [GHSA-4hqw-qxg8-jxx2](https://github.com/advisories/GHSA-4hqw-qxg8-jxx2) | Axios: Fetch Adapter Header Injection via Inherited FormData getHeaders |
| axios | moderate | `>=1.15.0 <1.20.0` | [GHSA-44g4-m2mj-wpvx](https://github.com/advisories/GHSA-44g4-m2mj-wpvx) | Axios: CIDR-form NO_PROXY entries are ignored, causing proxy exclusion bypass for internal IP ranges |
| axios | low | `=1.15.2` | [GHSA-654m-c8p4-x5fp](https://github.com/advisories/GHSA-654m-c8p4-x5fp) | Axios has a Patch Bypass: Proxy-Authorization Header Injection via Prototype Pollution — Incomplete Null-Prototype Fix |
| baseline-browser-mapping | moderate | `>=2.0.0 <2.11.0` | [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv) | baseline-browser-mapping process termination on invalid input causes denial of service |
| brace-expansion | high | `<1.1.16` | [GHSA-3jxr-9vmj-r5cp](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp) | brace-expansion: DoS via exponential-time expansion of consecutive non-expanding {} groups |
| brace-expansion | high | `<1.1.17` | [GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | brace-expansion: DoS via unbounded expansion length causing an out-of-memory process crash |
| brace-expansion | high | `>=4.0.0 <5.0.9` | [GHSA-rgw5-rvv9-x895](https://github.com/advisories/GHSA-rgw5-rvv9-x895) | brace-expansion: DoS via unbounded intermediate arrays, bypassing the CVE-2026-14257 mitigation |
| brace-expansion | high | `<1.1.20` | [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7) | brace-expansion: DoS via uncontrolled recursion on nested brace groups causing stack exhaustion |
| brace-expansion | high | `<1.1.19` | [GHSA-6j4f-fj2g-mc7p](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) | brace-expansion: DoS via uncontrolled recursion in parseCommaParts causing stack exhaustion |
| brace-expansion | moderate | `>=5.0.0 <5.0.6` | [GHSA-jxxr-4gwj-5jf2](https://github.com/advisories/GHSA-jxxr-4gwj-5jf2) | brace-expansion: Large numeric range defeats documented `max` DoS protection |
| brace-expansion | moderate | `<1.1.21` | [GHSA-q2hr-2g5m-vwhr](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr) | brace-expansion: Quadratic-time expansion of the `{a},b}` rewrite causes CPU denial of service |
| browserslist | high | `<=4.28.6` | [GHSA-c83g-rgw3-j3cx](https://github.com/advisories/GHSA-c83g-rgw3-j3cx) | Browserslist: Unbounded memory growth (no cache eviction) via distinct query results, leading to eventual OOM |
| browserslist | high | `<=4.28.6` | [GHSA-73wf-gq98-2v4g](https://github.com/advisories/GHSA-73wf-gq98-2v4g) | Browserslist: Uncaught crash / prototype write via untrusted browserslist-stats.json custom stats (normalizeStats) |
| fflate | moderate | `>=0.8.0 <0.8.3` | [GHSA-px8p-9vwx-vf98](https://github.com/advisories/GHSA-px8p-9vwx-vf98) | fflate unzipSync can enter an infinite loop when parsing malformed ZIP64 archives |
| follow-redirects | high | `>=1.16.0 <1.16.1` | [GHSA-q3jh-wrc6-jgq8](https://github.com/advisories/GHSA-q3jh-wrc6-jgq8) | follow-redirects array-form headers bypass cross-origin credential stripping |
| follow-redirects | high | `>=1.16.0 <1.16.1` | [GHSA-8r9p-f939-6h3c](https://github.com/advisories/GHSA-8r9p-f939-6h3c) | follow-redirects sensitiveHeaders regex escaping can expose credential headers |
| follow-redirects | high | `>=1.16.0 <=1.16.1` | [GHSA-mrwp-f3q8-3g9p](https://github.com/advisories/GHSA-mrwp-f3q8-3g9p) | follow-redirects: Cross-realm sensitiveHeaders arrays are discarded and custom credentials can follow redirects |
| form-data | high | `>=4.0.0 <4.0.6` | [GHSA-hmw2-7cc7-3qxx](https://github.com/advisories/GHSA-hmw2-7cc7-3qxx) | form-data: CRLF injection in form-data via unescaped multipart field names and filenames |
| js-yaml | high | `>=4.0.0 <4.3.0` | [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m) | js-yaml: YAML merge-key chains can force quadratic CPU consumption |
| js-yaml | high | `>=4.0.0 <4.3.1` | [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) | JS-YAML: Quadratic CPU consumption in !!omap resolution (3.x and 4.x) — CVE-2026-59870 fix not backported |
| js-yaml | high | `>=4.0.0 <4.3.2` | [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh) | js-yaml: maxTotalMergeKeys does not limit CPU use for empty merge sources |
| js-yaml | moderate | `>=4.0.0 <=4.1.1` | [GHSA-h67p-54hq-rp68](https://github.com/advisories/GHSA-h67p-54hq-rp68) | JS-YAML: Quadratic-complexity DoS in merge key handling via repeated aliases |
| maplibre-gl | critical | `<=6.4.0` | [GHSA-jrc7-96c5-q579](https://github.com/advisories/GHSA-jrc7-96c5-q579) | MapLibre GL JS: XSS Sanitizer Bypass in DOM.sanitize() via Live NamedNodeMap Removal Skip |
| minimatch | moderate | `>=7.0.0 <11.0.1` | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) | minimatch has potential denial of service via globparts amplification |
| nanoid | high | `<3.3.16` | [GHSA-28wg-ghj8-5hjv](https://github.com/advisories/GHSA-28wg-ghj8-5hjv) | nanoid: non-secure generators can loop indefinitely with negative size |
| nanoid | high | `<3.3.18` | [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) | nanoid: custom generators can loop indefinitely when size is zero |
| nanoid | high | `<3.3.12` | [GHSA-xwg4-73v4-xw9w](https://github.com/advisories/GHSA-xwg4-73v4-xw9w) | nanoid: Integer Overflow or Wraparound |
| next | critical | `>=16.0.0 <16.3.3` | [GHSA-p293-qw3h-jr36](https://github.com/advisories/GHSA-p293-qw3h-jr36) | Next.js: Unauthenticated Remote Code Execution on windows-hosted servers |
| next | critical | `>=16.0.0 <16.3.3` | [GHSA-2xp9-vwfh-vxw4](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4) | Next.js: Unauthenticated Remote Code Execution in Image Optimization API when AVIF files are used |
| next | critical | `>=16.2.0 <16.3.6` | [GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j) | Next.js: Remote Code Execution in next/og ImageResponse |
| next | critical | `>=16.0.0 <=16.4.0` | [GHSA-2464-fhr4-w9xw](https://github.com/advisories/GHSA-2464-fhr4-w9xw) | Next.js: Unauthenticated Remote Code Execution in Image Optimization API when SVG files are used |
| next | critical | `>=16.0.0 <=16.4.0` | [GHSA-673q-mjm6-r5xr](https://github.com/advisories/GHSA-673q-mjm6-r5xr) | Next.js: Unauthenticated Remote Code Execution in `use cache` functions returning typed arrays |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-8h8q-6873-q5fj](https://github.com/advisories/GHSA-8h8q-6873-q5fj) | Next.js Vulnerable to Denial of Service with Server Components |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-mg66-mrh9-m8jx](https://github.com/advisories/GHSA-mg66-mrh9-m8jx) | Next.js vulnerable to Denial of Service via connection exhaustion in applications using Cache Components |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-c4j6-fc7j-m34r](https://github.com/advisories/GHSA-c4j6-fc7j-m34r) | Next.js vulnerable to server-side request forgery in applications using WebSocket upgrades |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-492v-c6pp-mqqv](https://github.com/advisories/GHSA-492v-c6pp-mqqv) | Next.js has a Middleware / Proxy bypass through dynamic route parameter injection |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-267c-6grr-h53f](https://github.com/advisories/GHSA-267c-6grr-h53f) | Next.js has a Middleware / Proxy bypass in App Router applications via segment-prefetch routes |
| next | high | `>=16.0.0 <16.2.5` | [GHSA-36qx-fr4f-26g5](https://github.com/advisories/GHSA-36qx-fr4f-26g5) | Next.js has a Middleware / Proxy bypass in Pages Router applications using i18n |
| next | high | `>=16.0.0 <16.2.11` | [GHSA-6gpp-xcg3-4w24](https://github.com/advisories/GHSA-6gpp-xcg3-4w24) | Next.js: Middleware / Proxy bypass in App Router applications using Turbopack and single locale |
| next | high | `>=16.0.0 <16.2.11` | [GHSA-m99w-x7hq-7vfj](https://github.com/advisories/GHSA-m99w-x7hq-7vfj) | Next.js: Denial of Service in App Router using Server Actions |
| next | high | `>=16.0.0 <16.2.11` | [GHSA-89xv-2m56-2m9x](https://github.com/advisories/GHSA-89xv-2m56-2m9x) | Next.js: Server-Side Request Forgery in Server Actions on custom servers |
| next | high | `>=16.0.0 <16.2.11` | [GHSA-p9j2-gv94-2wf4](https://github.com/advisories/GHSA-p9j2-gv94-2wf4) | Next.js: Server-Side Request Forgery in rewrites via attacker-controlled destination hostname |
| next | high | `>=16.0.0 <16.3.8` | [GHSA-cjq9-62q9-8jv4](https://github.com/advisories/GHSA-cjq9-62q9-8jv4) | Next.js has Server-Side Request Forgery in Image Optimization |
| next | high | `>=16.0.0 <=16.4.0` | [GHSA-p3m5-59mp-jv5r](https://github.com/advisories/GHSA-p3m5-59mp-jv5r) | Next.js: Denial of Service in App Router using Server Actions |
| next | high | `>=16.0.0 <16.2.6` | [GHSA-26hh-7cqf-hhc6](https://github.com/advisories/GHSA-26hh-7cqf-hhc6) | Next.js has a Middleware / Proxy bypass in App Router applications via segment-prefetch routes - Incomplete Fix Follow-Up |
| next | moderate | `>=16.0.0 <16.2.5` | [GHSA-ffhc-5mcf-pf4q](https://github.com/advisories/GHSA-ffhc-5mcf-pf4q) | Next.js vulnerable to cross-site scripting in App Router applications using CSP nonces |
| next | moderate | `>=16.0.0 <16.2.5` | [GHSA-gx5p-jg67-6x7h](https://github.com/advisories/GHSA-gx5p-jg67-6x7h) | Next.js has cross-site scripting in beforeInteractive scripts with untrusted input |
| next | moderate | `>=16.0.0 <16.2.5` | [GHSA-h64f-5h5j-jqjh](https://github.com/advisories/GHSA-h64f-5h5j-jqjh) | Next.js has a Denial of Service in the Image Optimization API |
| next | moderate | `>=16.0.0 <16.2.5` | [GHSA-wfc6-r584-vfw7](https://github.com/advisories/GHSA-wfc6-r584-vfw7) | Next.js vulnerable to cache poisoning in React Server Component responses |
| next | moderate | `>=16.0.0 <16.2.11` | [GHSA-68g3-v927-f742](https://github.com/advisories/GHSA-68g3-v927-f742) | Next.js: Cache confusion of response bodies for requests with bodies |
| next | moderate | `>=16.0.0 <16.2.11` | [GHSA-4633-3j49-mh5q](https://github.com/advisories/GHSA-4633-3j49-mh5q) | Next.js: Cache confusion of response bodies for requests with bodies containing invalid UTF-8 byte sequences |
| next | moderate | `>=16.0.0 <16.2.11` | [GHSA-4c39-4ccg-62r3](https://github.com/advisories/GHSA-4c39-4ccg-62r3) | Next.js: Unbounded Server Action payload in Edge runtime |
| next | moderate | `>=16.0.0 <16.2.11` | [GHSA-q8wf-6r8g-63ch](https://github.com/advisories/GHSA-q8wf-6r8g-63ch) | Next.js: Denial of Service in the Image Optimization API using SVGs |
| next | moderate | `>=16.0.0 <16.2.11` | [GHSA-955p-x3mx-jcvp](https://github.com/advisories/GHSA-955p-x3mx-jcvp) | Next.js: Unauthenticated disclosure of internal Server Function endpoints |
| next | moderate | `>=16.0.0 <16.3.8` | [GHSA-4jqv-mc3x-m676](https://github.com/advisories/GHSA-4jqv-mc3x-m676) | Next.js has cache poisoning of SSG and ISR pages in self-hosted applications |
| next | moderate | `>=16.0.0 <16.3.8` | [GHSA-f87g-xv8r-7p7x](https://github.com/advisories/GHSA-f87g-xv8r-7p7x) | Next.js has information disclosure in App Router metadata image routes via dynamicParams bypass |
| next | moderate | `>=16.0.0 <16.3.8` | [GHSA-mcj8-r9mp-w47p](https://github.com/advisories/GHSA-mcj8-r9mp-w47p) | Next.js has cache poisoning in SSG/ISR rendering that leads to cross-user content substitution and persistent denial of service |
| next | moderate | `>=16.2.0 <=16.4.4` | [GHSA-vc7v-qv4w-wrv8](https://github.com/advisories/GHSA-vc7v-qv4w-wrv8) | Next.js: Cache leak across root param values in nested 'use cache' functions via delayed inner stream metadata |
| next | moderate | `>=16.0.0 <=16.4.4` | [GHSA-7qx7-33qx-rqx2](https://github.com/advisories/GHSA-7qx7-33qx-rqx2) | Next.js: SVG rejection bypass in the image optimization |
| next | moderate | `>=16.0.0 <=16.4.4` | [GHSA-f3mh-rxg3-f5g2](https://github.com/advisories/GHSA-f3mh-rxg3-f5g2) | Next.js: HttpOnly cookie exposure through internal response header on Next.js Edge runtime routes |
| next | moderate | `>=16.0.0 <=16.4.4` | [GHSA-pc58-hwjq-p385](https://github.com/advisories/GHSA-pc58-hwjq-p385) | Next.js: Cross-client response injection and disclosure in self-hosted Next.js applications forwarding fetched responses |
| next | moderate | `>=16.0.0 <=16.4.4` | [GHSA-rhh4-g77r-r9qj](https://github.com/advisories/GHSA-rhh4-g77r-r9qj) | Next.js: Cross-user cache disclosure and poisoning in Next.js use cache with binary arguments |
| next | low | `>=16.0.0 <16.2.5` | [GHSA-3g8h-86w9-wvmq](https://github.com/advisories/GHSA-3g8h-86w9-wvmq) | Next.js's Middleware / Proxy redirects can be cache-poisoned |
| next | low | `>=16.0.0 <16.2.5` | [GHSA-vfv6-92ff-j949](https://github.com/advisories/GHSA-vfv6-92ff-j949) | Next.js vulnerable to cache poisoning via collisions in React Server Component cache-busting |
| next | low | `>=16.0.0 <16.3.8` | [GHSA-39w2-rjm5-chcv](https://github.com/advisories/GHSA-39w2-rjm5-chcv) | Next.js has information disclosure in development server's Model Context Protocol endpoint |
| postcss | high | `<=8.5.11` | [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q) | PostCSS: Arbitrary file read and information disclosure via attacker-controlled sourceMappingURL in CSS comments |
| postcss | high | `<=8.5.17` | [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849) | PostCSS: Path Traversal in Previous Source Map Auto-Loading (sourceMappingURL) leads to Arbitrary .map File Disclosure |
| postcss | moderate | `<8.5.10` | [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93) | PostCSS has XSS via Unescaped </style> in its CSS Stringify Output |
| postcss | moderate | `<=8.5.22` | [GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp) | PostCSS: incomplete fix of GHSA-6g55-p6wh-862q — attacker-controlled sourceMappingURL reads arbitrary .map files when `from` is unset |
| sharp | high | `<0.35.0` | [GHSA-f88m-g3jw-g9cj](https://github.com/advisories/GHSA-f88m-g3jw-g9cj) | sharp inherited vulnerabilities in libvips: CVE-2026-33327, CVE-2026-33328, CVE-2026-35590, CVE-2026-35591 |
| sharp | high | `<0.35.4` | [GHSA-rgj7-g3m4-5g8c](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c) | sharp: Vulnerabilities in libheif: GHSA-g89c-p67h-r497 and GHSA-2jg2-4ch7-h545 |
| sharp | high | `<0.35.5` | [GHSA-wq5f-xc86-pv6w](https://github.com/advisories/GHSA-wq5f-xc86-pv6w) | sharp : Vulnerability in librsvg dependency CVE-2026-96889 |
| source-map-js | high | `>=1.0.0 <1.2.2` | [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) | source-map-js allows event-loop denial of service through indexed source-map section offsets |
| zod | high | `<4.6.6` | [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) | Zod can exhaust memory while validating oversized constrained collections |

## Appendix B — Backend advisories before the upgrade (OSV, `pip freeze` of the shipped image)

All 25 resolved — fixed by upgrade, or the package removed with python-jose (OSV → 0). PYSEC records that alias a listed GHSA are omitted.

| Package (as shipped) | Severity | Advisory | CVE | Fixed in | Title |
|---|---|---|---|---|---|
| dnspython==2.9.0 | HIGH | [GHSA-vvf4-9x63-8xvv](https://osv.dev/vulnerability/GHSA-vvf4-9x63-8xvv) | CVE-2026-128089 | 2.9.2 | dnspython has excessive memory and CPU use |
| ecdsa==0.19.2 | HIGH | [GHSA-wj6h-64fc-37mp](https://osv.dev/vulnerability/GHSA-wj6h-64fc-37mp) | CVE-2024-23342 | **none** | Minerva timing attack on P-256 in python-ecdsa |
| pyasn1==0.6.4 | HIGH | [GHSA-2qm8-x737-gmw5](https://osv.dev/vulnerability/GHSA-2qm8-x737-gmw5) | CVE-2026-119196 | 0.6.5 | pyasn1 has quadratic CPU consumption in constructed BIT STRING decoding |
| pyasn1==0.6.4 | HIGH | [GHSA-9m75-vc3g-4x39](https://osv.dev/vulnerability/GHSA-9m75-vc3g-4x39) | CVE-2026-119195 | 0.6.5 | pyasn1 has quadratic-time denial of service in constructed string and indefinite-length ANY decoding |
| pyasn1==0.6.4 | HIGH | [GHSA-fm9c-5rcf-2q5p](https://osv.dev/vulnerability/GHSA-fm9c-5rcf-2q5p) | CVE-2026-119194 | 0.6.5 | pyasn1 has quadratic CPU use in schemaless BER/CER/DER container decoding |
| pyasn1==0.6.4 | HIGH | [GHSA-mm57-4v3p-rchx](https://osv.dev/vulnerability/GHSA-mm57-4v3p-rchx) | CVE-2026-119197 | 0.6.5 | pyasn1 has quadratic-complexity denial of service in binary REAL decoding |
| python-dotenv==1.0.1 | MODERATE | [GHSA-mf9w-mj56-hr94](https://osv.dev/vulnerability/GHSA-mf9w-mj56-hr94) | CVE-2026-28684 | 1.2.2 | python-dotenv: Symlink following in set_key allows arbitrary file overwrite via cross-device rename fallback |
| python-jose==3.3.0 | CRITICAL | [GHSA-3qf3-8w2g-rqmx](https://osv.dev/vulnerability/GHSA-3qf3-8w2g-rqmx) | CVE-2024-33663,CVE-2026-85394 | **none** | python-jose algorithm confusion guard bypassed by DER-encoded public keys |
| python-jose==3.3.0 | CRITICAL | [GHSA-6c5p-j8vq-pqhj](https://osv.dev/vulnerability/GHSA-6c5p-j8vq-pqhj) | CVE-2024-33663,CVE-2026-85394 | 3.4.0 | python-jose algorithm confusion with OpenSSH ECDSA keys |
| python-jose==3.3.0 | MODERATE | [GHSA-cjwg-qfpm-7377](https://osv.dev/vulnerability/GHSA-cjwg-qfpm-7377) | CVE-2024-33664 | 3.4.0 | python-jose denial of service via compressed JWE content |
| python-jose==3.3.0 | n/a | [PYSEC-2025-185](https://osv.dev/vulnerability/PYSEC-2025-185) | CVE-2024-29370 | **none** | python-jose (no summary in OSV) |
| python-multipart==0.0.20 | HIGH | [GHSA-5rvq-cxj2-64vf](https://osv.dev/vulnerability/GHSA-5rvq-cxj2-64vf) | CVE-2026-53539 | 0.0.30 | python-multipart: Quadratic-time querystring parsing with semicolon separators causes CPU denial of service |
| python-multipart==0.0.20 | HIGH | [GHSA-pp6c-gr5w-3c5g](https://osv.dev/vulnerability/GHSA-pp6c-gr5w-3c5g) | CVE-2026-42561 | 0.0.27 | python-multipart has Denial of Service via unbounded multipart part headers |
| python-multipart==0.0.20 | HIGH | [GHSA-wp53-j4wj-2cfg](https://osv.dev/vulnerability/GHSA-wp53-j4wj-2cfg) | CVE-2026-24486 | 0.0.22 | Python-Multipart has Arbitrary File Write via Non-Default Configuration |
| python-multipart==0.0.20 | LOW | [GHSA-6jv3-5f52-599m](https://osv.dev/vulnerability/GHSA-6jv3-5f52-599m) | CVE-2026-53538 | 0.0.30 | python-multipart: Semicolon treated as querystring field separator enables parameter smuggling |
| python-multipart==0.0.20 | LOW | [GHSA-v9pg-7xvm-68hf](https://osv.dev/vulnerability/GHSA-v9pg-7xvm-68hf) | CVE-2026-53540 | 0.0.31 | python-multipart: Negative Content-Length in parse_form buffers the entire body in memory |
| python-multipart==0.0.20 | LOW | [GHSA-vffw-93wf-4j4q](https://osv.dev/vulnerability/GHSA-vffw-93wf-4j4q) | CVE-2026-53537 | 0.0.30 | python-multipart: Content-Disposition parameter smuggling via RFC 2231/5987 extended parameters |
| python-multipart==0.0.20 | MODERATE | [GHSA-mj87-hwqh-73pj](https://osv.dev/vulnerability/GHSA-mj87-hwqh-73pj) | CVE-2026-40347 | 0.0.26 | python-multipart affected by Denial of Service via large multipart preamble or epilogue data |
| starlette==0.41.3 | HIGH | [GHSA-7f5h-v6xp-fcq8](https://osv.dev/vulnerability/GHSA-7f5h-v6xp-fcq8) | CVE-2025-62727 | 0.49.1 | Starlette vulnerable to O(n^2) DoS via Range header merging in ``starlette.responses.FileResponse`` |
| starlette==0.41.3 | HIGH | [GHSA-82w8-qh3p-5jfq](https://osv.dev/vulnerability/GHSA-82w8-qh3p-5jfq) | CVE-2026-54283 | 1.3.1 | Starlette: request.form() limits silently ignored for application/x-www-form-urlencoded enable DoS |
| starlette==0.41.3 | HIGH | [GHSA-wqp7-x3pw-xc5r](https://osv.dev/vulnerability/GHSA-wqp7-x3pw-xc5r) | CVE-2026-48818 | 1.1.0 | Starlette: SSRF and NTLM credential theft via UNC paths in StaticFiles on Windows |
| starlette==0.41.3 | LOW | [GHSA-jp82-jpqv-5vv3](https://osv.dev/vulnerability/GHSA-jp82-jpqv-5vv3) | CVE-2026-54282 | 1.3.0 | Starlette: Unvalidated request path concatenated into authority poisons request.url.hostname |
| starlette==0.41.3 | MODERATE | [GHSA-2c2j-9gv5-cj73](https://osv.dev/vulnerability/GHSA-2c2j-9gv5-cj73) | CVE-2025-54121 | 0.47.2 | Starlette has possible denial-of-service vector when parsing large files in multipart forms |
| starlette==0.41.3 | MODERATE | [GHSA-86qp-5c8j-p5mr](https://osv.dev/vulnerability/GHSA-86qp-5c8j-p5mr) | CVE-2026-48710 | 1.0.1 | Starlette has missing Host header validation that poisons request.url.path, bypassing path-based security chec |
| starlette==0.41.3 | MODERATE | [GHSA-x746-7m8f-x49c](https://osv.dev/vulnerability/GHSA-x746-7m8f-x49c) | CVE-2026-48817 | 1.1.0 | Starlette: Arbitrary HTTP method dispatched to `HTTPEndpoint` attributes via `getattr` |
