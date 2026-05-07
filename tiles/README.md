# Tiles

This directory holds the self-hosted basemap used by the `/map` page. The `.pmtiles` binary is gitignored (expect roughly 5–6 GB at maxzoom 14, more without a zoom cap); only this README and `.gitkeep` are tracked.

At runtime, Caddy bind-mounts this folder read-only to `/srv/tiles` inside the container and serves its contents under `https://<site>/tiles/*`. HTTP Range requests are supported out-of-the-box, which is what the `pmtiles` browser library relies on to fetch individual tile bytes from the single-file archive.

## Expected file

```
tiles/canada.pmtiles
```

## How to obtain

### Option 1 — extract from a Protomaps daily build (recommended)

Install `go-pmtiles` (<https://github.com/protomaps/go-pmtiles/releases>), then:

```
pmtiles extract https://build.protomaps.com/<YYYYMMDD>.pmtiles canada.pmtiles \
  --bbox=-141.0,41.5,-52.0,83.5 --maxzoom=14
```

- Replace `<YYYYMMDD>` with a recent build date (Protomaps keeps a rolling window of nightly builds).
- The bounding box covers mainland Canada plus the Arctic archipelago.
- **`--maxzoom=14` is important.** Without it `pmtiles extract` pulls every zoom level the source has (z15+ for highly populated areas), which roughly doubles the file size and adds detail beyond what `/map` actually renders. With `--maxzoom=14`, expect ~5–6 GB; without it, expect 10+ GB.

### Option 2 — pull a full planet and extract locally

Download a Protomaps planet archive, then run the same `pmtiles extract` command locally. Slower for the first download but lets you re-extract different regions without re-fetching.

## Enabling it in dev

After placing the file at `tiles/canada.pmtiles`, set in `.env`:

```
NEXT_PUBLIC_TILES_URL=/tiles/canada.pmtiles
```

(Root-relative — works through Caddy on `localhost`, on a Cloudflare quick tunnel, and on the production domain without rebuild.)

Rebuild the frontend so the URL is baked into the client bundle:

```
docker compose up --build frontend
```

Leave `NEXT_PUBLIC_TILES_URL` blank to fall back to CartoDB Voyager (useful before the file is downloaded).
