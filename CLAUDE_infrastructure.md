# Infrastructure & Deployment Architecture

## Hosting Strategy
- **Primary target:** Single VPS (Hetzner CAX11 or DigitalOcean $6 droplet) running Docker Compose
- Domain: waterpulse.ca
- Self-hosted — no managed services (no Vercel, no Supabase, no AWS)
- `k8s/` manifests exist in the repo as an alternative deployment path but are not the primary target for single-VPS hosting. If k8s manifests fall more than one minor compose change behind, either update them or delete — do not let stale manifests accumulate.

## Service Topology (4 services)
```
services:
  caddy       → ports 80, 443 exposed
                  /api/*, /docs, /openapi.json → backend:8000
                  /tiles/*                     → static PMTiles (provisional, see below)
                  /*                           → frontend:3000
  frontend    → Next.js (standalone build, port 3000 internal only)
  backend     → FastAPI (Python 3.12, uvicorn, port 8000 internal only)
                  Runs Alembic migrations, APScheduler, serves /api/*
                  ⚠ APScheduler means backend MUST stay at replica count = 1.
                  If horizontal scaling is ever needed, extract scheduling to an
                  external cron trigger or implement leader election first.
                  (This is why k8s/job-historical-sync.yaml exists as a CronJob
                  on the k8s path — to avoid double-scheduling with multiple replicas.)
  db          → PostgreSQL 16 (port 5432 internal only, data on named volume `pgdata`)
```

## Migration Path (staged — do in order)
1. **Accept this doc** as canonical deployment direction after topology review
2. **nginx → Caddy migration** (feature branch) — rewrite proxy config from `nginx/default.conf` to `Caddyfile`, update `docker-compose.yml`, update `CLAUDE.md` "How They Connect" section. Set `Secure=True`, `SameSite=Lax` cookie flags in backend config as part of this step (Caddy provides HTTPS from first boot via automatic Let's Encrypt).
3. **PMTiles implementation** (feature branch, per existing deferred plan) — Track A only (local Caddy serving at `/tiles/*` path, NOT `tiles.waterpulse.ca` subdomain — this is a deliberate change from the earlier plan; update the PMTiles plan's verification steps accordingly). Drop Track B (R2 fallback). The `/tiles/*` Caddy route is provisional until this ships.
4. **VPS provisioning** — actual server setup, `pg_dump` cron, GitHub Actions deploy pipeline, secrets deployment
5. **Cleanup** — retire AWS deployment plan, update `project_pmtiles_plan.md` to reflect Track B removal and subdomain→path change

## Build-time Configuration
- `NEXT_PUBLIC_API_URL` is baked at build time via Docker build args (see `docker-compose.yml`, frontend service `build.args` block)
- For VPS production: set `NEXT_PUBLIC_API_URL=/api` in build args so Caddy handles routing — do NOT rely on runtime env vars for this

## Architecture Note: ARM vs x86
- Hetzner CAX-series is ARM64 (Ampere). If the dev machine builds `linux/amd64` images, they will not run on CAX.
- Options: build on-server with `docker compose build` (simplest for small projects), use `docker buildx build --platform linux/arm64`, or use Hetzner CX-series (x86) to avoid the issue entirely.

## Backups
- Nightly `pg_dump` via `docker compose exec` against the running db container:
  ```
  docker compose exec -T db pg_dump -U waterpulse waterpulse | gzip > backup_$(date +%F).sql.gz
  ```
- Store backups off-server (scp to local machine, or Hetzner object storage)
- Automate via cron on the host

## Secrets Management
- `.env` at repo root is the current source of truth (read by `docker-compose.yml` via `env_file`)
- Already gitignored — do not commit
- Initial `.env` copied to VPS via `scp`; rotated manually on the server
- Acceptable for single-operator portfolio project; revisit if collaborators gain server access

## CI/CD
- **Chosen approach (Option B — build on server):** GitHub Actions SSHes into VPS and runs `git pull && docker compose up -d --build`
- Simpler than Option A (build images → push to GHCR → pull on server) — no container registry to manage
- Tradeoff: deploys are slower (build happens on VPS) but acceptable for a ~10-user/day app on a small server
- GHA workflow needs an SSH key stored as a repository secret

## Constraints
- Budget: ~$10–12 CAD/month total
- Traffic: ~10 users/day max (summer), near-zero in winter
- Database: ~5 GB currently, expected under 7 GB for years
- PMTiles: ~6 GB static files (not yet implemented — deferred to feature branch)
- Repo: ~2 GB
- Hetzner CAX11 egress allowance: 20 TB/month — far above projected needs. No R2 fallback required.

## Disk Budget (Hetzner CAX11 = 40 GB)
```
DB data:                ~5 GB (growing to 7 GB)
PMTiles:                ~6 GB
Repo:                   ~2 GB
Docker images:          ~2 GB (postgres + frontend + backend + caddy)
Docker build cache:     ~3–5 GB
Logs, OS, swap:         ~5 GB
────────────────────────────────
Estimated total:        ~23–27 GB of 40 GB
```
Comfortable but not roomy. Run `docker system prune` monthly. Consider a simple cron that emails or logs disk usage warnings above 80%.

## Key Decisions
- Caddy over nginx (simpler config, automatic TLS via Let's Encrypt) — this is a migration from the current nginx setup
- Docker Compose is the primary deployment tool for single-VPS hosting
- k8s manifests are retained for cloud/multi-node scenarios but are not actively maintained for this deployment target
- No CDN needed at current traffic levels (Cloudflare proxy-off for DNS-only + free DDoS protection is a zero-cost option if desired later)
- Rate limiter: in-memory slowapi is sufficient for VPS single-instance (no Redis needed)
- PMTiles served at `/tiles/*` path (not `tiles.waterpulse.ca` subdomain) — simpler on single VPS (one cert, one service)

## Resolved: Prior Competing Plans
- **AWS deployment** (`project_aws_deployment.md`): Retired. Overkill for traffic/budget. EC2 + RDS + S3 minimum ~$40–80 CAD/month for no meaningful benefit at this scale. Rate limiter note in that doc (needs Redis) is superseded — in-memory slowapi is correct for single-instance VPS.
- **Home self-host via Cloudflare Tunnel**: Retired. ISP asymmetric upload bandwidth throttles user experience, dynamic IP requires DDNS workarounds, power/router outages cause downtime for a portfolio project, and exposes home network attack surface.
- **Vercel Hobby + free-tier split hosting**: Evaluated and rejected. Vercel only hosts Next.js — FastAPI backend and PostgreSQL would need separate free-tier providers (Render, Railway, Supabase/Neon), each with cold starts and storage caps. The 5 GB database exceeds most free Postgres tiers. Cross-provider architecture fragments ops, multiplies failure modes, and cold starts on 2+ services defeat the fast-load-times goal. A $6–10/month VPS with zero cold starts is cheaper in time and equivalent in cost.
- **VPS (this plan)**: Canonical.
