# Architecture

How Denver Neighborhood Sales fits together, from city data to the page Garrett looks at.

```
Denver open data (ArcGIS REST)           FRED (CPI)
        │                                    │
        ▼                                    │
scripts/fetch.py ── data/raw/*.csv.gz ──► scripts/build.py ──► docs/data.json
  guards: row minimums,                   guards: publish only if      docs/neighborhoods.geojson
  neighborhood match ≥95%                 sales don't drop >10%              │
                                                                             ▼
                              GitHub Pages (main /docs) ──► index.html (dashboard) + map.html (map)
                                                               both load docs/js/common.js
```

Everything runs in **GitHub Actions** (`.github/workflows/refresh.yml`): every Monday at 13:00 UTC, on manual dispatch, and on any push that touches pipeline or page code. The bot commits changed data back to `main`; GitHub Pages republishes `docs/` about a minute later.

## Files

| Path | Role |
|---|---|
| `scripts/config.py` | **The one place to change coverage**: the neighborhood list (name, cluster, display order), display-name fixes, which deed types count as market sales. |
| `scripts/fetch.py` | Pulls four Denver tables with keyset pagination, places every single-family parcel in a statistical neighborhood (point-in-polygon), strips buyer/seller names to flags, writes `data/raw/`. Aborts, keeping last week's data, if a table looks partially loaded. |
| `scripts/build.py` | Applies the cleaning funnel, converts coordinates to lat/lon, attaches CPI, writes `docs/data.json` and simplified boundaries. Refuses to publish if clean sales fall >10% or columns disappear. |
| `data/raw/` | Committed raw pulls (gzipped CSV + boundary GeoJSON). Lets anyone re-run `build.py` without network access to Denver. |
| `docs/index.html` | Dashboard: filters, headline tiles, every-sale / trend chart, neighborhood table, neighborhood pages with every sale, Zillow links. |
| `docs/map.html` | Full-screen map: one pin per home at its latest qualifying sale, synced list, popups with sale history. |
| `docs/js/common.js` | Helpers both pages share: formatting, Zillow URLs, data loading by column name, the shared saved-filters store. |
| `docs/vendor/` | Self-hosted MapLibre GL 5.24 (BSD license included). No CDN dependency. |
| `requirements.txt` | Pinned Python packages the pipeline was verified with. |
| `tests/smoke_test.py` | 17 browser checks across both pages and phone width. |
| `handbook/` | These docs. |

## The data contract: `docs/data.json`

```jsonc
{
  "meta": {
    "built": "2026-09-25T04:21+00:00",      // UTC build time
    "latest_recorded": "2026-09-04",         // newest deed recording date in the data
    "beds_mode": "beds" | "sqft",            // "sqft" = Denver's bed/bath table was incomplete this run
    "default_min_sqft": 0,                   // 1400 in sqft mode (proxy for 3 bd / 2 ba)
    "cleaning": [{ "step": "...", "rows": 37475 }, ...],   // funnel shown on the dashboard
    "neighborhoods": [{ "name", "cluster", "parcels" }],  // index = the "nbhd" value in each row
    "columns": ["date","nbhd","price","sqft","year_built","lot_sqft","zone","address",
                "recorded","beds","baths","zip","pid","lat","lon"]
  },
  "cpi": { "2014-12": 234.8, ... },          // US CPI-U monthly, or null if FRED was unreachable
  "sales": [[...], ...]                      // one array per clean sale, in "columns" order
}
```

**Rules for changing it:** pages look columns up **by name** (`DNSD.loadData`), so adding a column at the end is always safe. Renaming or removing one breaks the pages, and `build.py` refuses to publish if a column vanishes (except beds/baths, which legitimately drop out in sqft mode). The `nbhd` value is an index into `meta.neighborhoods`, which follows `config.py` order. Saved selections in the browser use names, so reordering is safe.

## Front end

- Plain HTML, CSS and JavaScript. No build step, no framework. Each page is one file plus `js/common.js`.
- **Shared saved filters.** Both pages read and write one `localStorage` key (`dnsd2`) and merge on save, so price, size, date range and 3/2 settings carry between dashboard and map.
- **Charts** are hand-built SVG following the dataviz method: fixed categorical color slots (max 3 compared at once), a sequential blue ramp for magnitude, a validated palette in light and dark modes, hover tooltips, and a table for every chart.
- **Map base layers:** CARTO Voyager (light), CARTO Dark Matter (dark), Esri World Imagery (satellite). All are free, keyless, and attributed. If a base style fails to load, the page falls back to a plain background and the pins keep working.
- Everything user-supplied or from data is inserted with `textContent`, never `innerHTML`.
