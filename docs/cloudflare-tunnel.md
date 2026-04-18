# Cloudflare Quick Tunnel — Remote & Mobile Testing

A running Docker Compose stack on your dev machine only answers to `http://localhost`
and `http://<LAN-IP>`. Neither of those origins is a "secure context" in the
browser's eyes, which means:

- **Geolocation is blocked.** `navigator.geolocation.getCurrentPosition()` only
  works on HTTPS origins (or `localhost`). Testing the "Locate Me" button from a
  phone or other machine via the LAN IP fails silently.
- **iOS Safari applies stricter resource caps** to insecure origins, which has
  masked real bugs in the past.
- **Some browser APIs (clipboard, service workers, WebAuthn)** refuse to run at
  all over plain HTTP.

A Cloudflare **Quick Tunnel** solves this with zero config: it gives you a free,
temporary, public HTTPS URL that forwards all traffic back to your local dev
stack. This is the right tool for *ad-hoc testing only* — not for production
hosting, and not as a permanent remote-access solution. The canonical production
plan is the single-VPS Docker Compose deploy described in
[CLAUDE_infrastructure.md](../CLAUDE_infrastructure.md).

---

## How it works

```
Phone / remote browser
         │  HTTPS
         ▼
https://<random>.trycloudflare.com   ← issued by Cloudflare, valid TLS cert
         │
         │   (Cloudflare global edge network)
         │
         ▼
cloudflared process on your Windows machine
         │  HTTP
         ▼
http://localhost:80  →  Caddy container  →  frontend / backend / tiles
```

`cloudflared` is a small CLI that opens an **outbound** connection (QUIC, falls
back to HTTPS) from your machine to Cloudflare's network. No inbound ports are
opened, no DNS record is needed, no router configuration changes. Cloudflare
assigns a random `*.trycloudflare.com` subdomain that already sits behind their
wildcard TLS certificate, so browsers trust it immediately with no cert install.

Incoming requests to that subdomain hit Cloudflare's edge, travel back through
the outbound tunnel, and are delivered to `http://localhost:80` on your machine,
where Caddy is already listening and routing `/api/*`, `/tiles/*`, and `/*` to
the right containers.

### Why the app works unchanged through the tunnel

Because [src/lib/api.js](../waterpulse-frontend/src/lib/api.js) defaults
`NEXT_PUBLIC_API_URL` to the empty string (same-origin relative requests) and
`NEXT_PUBLIC_TILES_URL` in `.env` is `/tiles/canada.pmtiles` (root-relative),
the frontend JS bundle makes all requests to whatever host it was loaded from.
Open the tunnel URL → API calls go to the tunnel URL → Caddy routes them
correctly. No rebuild is required when the tunnel URL changes.

---

## Prerequisites

- `cloudflared` installed (one-time).
- The WaterPulse Docker Compose stack already running (`docker compose up -d`),
  with Caddy exposed on port 80.
- Windows 11; Bash or PowerShell.

### Installing cloudflared (Windows)

```bash
winget install --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

After install, the binary lives at `C:\Program Files (x86)\cloudflared\cloudflared.exe`.
It is not automatically added to the current shell's `PATH` — open a new
terminal, or use the absolute path below.

Verify:

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" --version
```

You should see something like `cloudflared version 2025.8.1`.

---

## Starting a tunnel

From any directory (path is irrelevant — the tunnel targets `localhost:80`,
which is Caddy on the host):

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://localhost:80
```

Or if `cloudflared` is on your `PATH`:

```bash
cloudflared tunnel --url http://localhost:80
```

After a few seconds you'll see output like:

```
INF Your quick Tunnel has been created! Visit it at:
INF https://requests-arnold-oaks-contacts.trycloudflare.com
INF Registered tunnel connection
```

Open that URL on the phone / remote machine and the app loads over HTTPS.

### Leaving it running in the background

The process must stay alive for the tunnel to work. Options:

- **Foreground in a dedicated terminal** — easy to see logs; Ctrl+C to stop.
- **Background via `&` in bash** —
  `cloudflared tunnel --url http://localhost:80 > tunnel.log 2>&1 &`
  then `tail -f tunnel.log` to grab the URL.
- **Windows Service** — for long-lived use, `cloudflared` can run as a service,
  but that's only worth setting up for a named tunnel (see below).

---

## Stopping the tunnel

- **Foreground:** Ctrl+C in the terminal where it's running.
- **Background:** find the process and kill it.

```bash
# Find the PID
tasklist //FI "IMAGENAME eq cloudflared.exe"

# Kill it
taskkill //F //IM cloudflared.exe
```

---

## Lifetime, limits, and gotchas

- **The URL is ephemeral.** Restart the tunnel → new random subdomain. Don't
  bookmark it, don't share it as a permanent link.
- **No uptime guarantee.** Cloudflare's terms reserve the right to terminate
  quick tunnels. In practice they're stable for days to weeks unless abused.
- **Dies on process exit.** Terminal close, Ctrl+C, machine sleep/shutdown, VPN
  switch that kills the outbound connection, or a long internet outage — all
  end the tunnel. Restart `cloudflared` to get a new URL.
- **Only one active URL per process.** Run the command twice → two tunnels,
  two different URLs.
- **Not for production.** Rate-limited, no uptime SLA, no custom domain. For
  actual remote access use the VPS deployment (real domain, Let's Encrypt cert
  via Caddy) or set up a Cloudflare *named* tunnel (below).

### Cookie & CORS notes

Because the backend uses SameSite=Lax HTTPOnly cookies for auth, login works
over the tunnel URL as long as both frontend and backend are served from the
**same origin** (i.e., the tunnel URL). Caddy already co-locates them, so this
is automatic — nothing to configure.

`COOKIE_SECURE=False` in your `.env` is fine for tunnel testing. The cookie is
sent over Cloudflare's HTTPS leg regardless; it only becomes `Secure`-flagged
when you switch to real production HTTPS on the VPS.

---

## If you need a persistent URL: named tunnels

A **named tunnel** is tied to your Cloudflare account and keeps the same URL
across restarts. It requires a free Cloudflare account and a domain registered
with Cloudflare DNS. Setup is roughly:

1. `cloudflared tunnel login` → opens a browser to auth with Cloudflare.
2. `cloudflared tunnel create waterpulse-dev` → creates a tunnel resource.
3. Add a DNS record (`cloudflared tunnel route dns waterpulse-dev dev.waterpulse.ca`).
4. Write a `config.yml` mapping ingress rules to `localhost:80`.
5. `cloudflared tunnel run waterpulse-dev` → starts the tunnel with that
   stable hostname.

See [Cloudflare's named-tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
for details. For a portfolio-stage project, quick tunnels are usually enough
for sporadic mobile testing, and the real production deploy is the VPS path.

---

## Why this exists: what it diagnosed

The tunnel was added to the toolbox while chasing an iOS-only map crash: on
iPhone over `http://<LAN-IP>/map`, Safari terminated the tab shortly after any
pan or zoom. Two hypotheses needed splitting:

1. **iOS is tightening resources on insecure origins** → would be fixed by HTTPS.
2. **MapLibre/PMTiles is doing something iOS dislikes regardless of origin.**

By serving the exact same bundle over a trusted HTTPS URL (this tunnel) we
ruled out #1 in a few minutes — the crash persisted over HTTPS. That pointed us
at the real culprit: per-frame `sessionStorage` writes from Zustand's persist
middleware and per-frame `history.replaceState` calls from the URL sync effect.
Fix details are in the code comments at
[src/stores/mapStore.js:119-133](../waterpulse-frontend/src/stores/mapStore.js#L119-L133)
and [src/app/map/page.js:62-84](../waterpulse-frontend/src/app/map/page.js#L62-L84),
and the rule is captured in the frontend CLAUDE.md.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` in `cloudflared` logs | Caddy isn't listening on `:80` | `docker compose ps` — is `waterpulse-caddy-1` up? |
| Phone loads tunnel URL but sees Cloudflare error page (1033, 502, etc.) | Tunnel still connecting, or local stack down | Wait 10–20 sec after the "Your quick Tunnel has been created" line; verify locally with `curl -I http://localhost/` |
| Tunnel URL works but API calls 404 | Frontend bundle was built with an old `NEXT_PUBLIC_API_URL` | Rebuild frontend: `docker compose up -d --build frontend` |
| Tiles 404 on tunnel URL | `NEXT_PUBLIC_TILES_URL` not set, or `canada.pmtiles` missing from `tiles/` | Check `.env` and `ls tiles/` |
| Tunnel drops after a few hours | Cloudflare edge cycled, or your internet hiccuped | Restart `cloudflared`; get a new URL |
| "locate me" still blocked on the tunnel URL | iOS permission was denied once and cached | Settings → Safari → Location → Allow, or clear site data for that hostname |
