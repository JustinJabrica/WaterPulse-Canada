# Tiles

This directory holds the self-hosted basemap used by the `/map` page. The `.pmtiles` binary is gitignored (expect ~5–6 GB for a Canada extract); only this README and `.gitkeep` are tracked.

At runtime, Caddy bind-mounts this folder read-only to `/srv/tiles` inside the container and serves its contents under `https://<site>/tiles/*`. HTTP Range requests are supported out-of-the-box, which is what the `pmtiles` browser library relies on to fetch individual tile bytes from the single-file archive.

## Expected file

```
tiles/canada.pmtiles
```

## How to obtain

### Option 1 — extract from a Protomaps daily build (recommended)

Install `go-pmtiles` (<https://github.com/protomaps/go-pmtiles/releases>), then:

```
pmtiles extract https://build.protomaps.com/20260101.pmtiles canada.pmtiles \
  --bbox=-141.0,41.5,-52.0,83.5
```

Replace `YYYYMMDD` with a recent build date (Protomaps keeps a rolling window). The bounding box above covers mainland Canada plus the Arctic archipelago.

### Option 2 — pull a full planet and extract locally

Download a Protomaps planet archive, then run the same `pmtiles extract` command locally. Slower for the first download but lets you re-extract different regions without re-fetching.

## Enabling it in dev

After placing the file at `tiles/canada.pmtiles`, set in `.env`:

```
NEXT_PUBLIC_TILES_URL=http://localhost/tiles/canada.pmtiles
```

Rebuild the frontend so the URL is baked into the client bundle:

```
docker compose up --build frontend
```

Leave the variable blank to fall back to CartoDB Voyager (useful before the file is downloaded).
