# Roadmap and decision log

## Backlog

Ranked by how much each one sharpens the actual buy decision. Pick from the top unless Garrett redirects.

| # | Idea | Why it matters | Size | Notes |
|---|---|---|---|---|
| 1 | **Comps tool:** enter an address, get the 10 most similar recent sales (same neighborhood, ±20% size, beds/baths, age) with median $/sq ft | The question every offer comes down to | M | Pure front end on existing data. |
| 2 | **Watchlist and alerts:** star homes or streets; weekly email when something on the list sells | Turns the weekly refresh into a signal | M | Needs an email path (GitHub Actions → SMTP or a Resend key stored as a repo secret). |
| 3 | **Weekly "what changed" note** written by Claude | Summary without opening the dashboard | S–M | Anthropic API key as an Actions secret; Haiku extracts, a stronger model writes; costs a few cents a week. |
| 4 | **Building permits overlay** (ADUs, additions, new builds) | Spots scrape-and-rebuild pressure and ADU precedent by block | M | Denver open data has permits; join on parcel. |
| 5 | **Lot and ADU feasibility filter** (lot size, alley access, existing garage) | ADUs are legal citywide since Nov 2024; the lot is what matters | M | Lot size exists today; alley access would need street/alley centerlines. |
| 6 | **Pre-2015 history** via FHFA zip-level House Price Index | Shows the full 2008 cycle | S | An index, not per-sale data; a separate line on the trend view. |
| 7 | **Days on market / list-to-sale ratio** | Market heat per neighborhood | L | Needs MLS data (agent export or a licensed feed). Public records don't have listings. |
| 8 | **Street View thumbnails** on map cards | Zillow feel | S | Google Static Street View API key with billing; pennies/month. |
| 9 | **CSV export** of any filtered view | Share with an agent or a lender | S | Front end only. |
| 10 | **Rent context** (Census ACS by tract, Zillow ZORI by zip) | House-hack / ADU income math | M | Zip- or tract-level only. |

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-09-23 | Build on public Denver open data, refreshed weekly, not MLS | Free and legal, and trend clarity matters more than same-day listings 12+ months before buying. MLS is the upgrade once actively shopping. |
| 2026-09-23 | GitHub Actions + GitHub Pages (public repo) | Free, durable, no laptop dependency. Names are stripped before commit, so the public repo holds only public-record facts. |
| 2026-09-23 | Official statistical neighborhoods via point-in-polygon, not the assessor's neighborhood field | The assessor's codes don't match the 78 official boundaries. |
| 2026-09-23 | Fail closed: guards abort the run and keep last week's data | Denver reloads and truncates tables; a partial week must never overwrite good data. |
| 2026-09-23 | History starts 2015 | The sales API holds nothing earlier. |
| 2026-09-23 | Sq-ft proxy (1,400+) for 3 bd / 2 ba while Denver's bed/bath table was truncated | Chosen over scraping 26k property pages. Replaced by true beds/baths when the table returned Sep 24 (13% of real 3/2 sales are under 1,400 sq ft). |
| 2026-09-23 | Drop the "ADU-eligible zoning" flag | Denver legalized ADUs in all residential zones in Nov 2024; zoning no longer discriminates. |
| 2026-09-24 | Add City Park, City Park West, Congress Park, Cherry Creek; Central cluster (Cheesman moves there) | Garrett's request; Cheesman sits between those areas geographically. |
| 2026-09-24 | "Every sale" scatter is the default chart; sale price the default measure | Garrett wants to see actual sales, not only medians. |
| 2026-09-24 | Compare at most 3 neighborhoods on a chart | The 4th palette slot fails colorblind separation in scatter views. |
| 2026-09-24 | Rolling median widens to 6 or 12 months for thin neighborhoods | Cherry Creek and City Park have about 9 qualifying sales a year. |
| 2026-09-24 | Price filter is a min–max range; the top of the scale means no max | Budget ceilings are the common case. |
| 2026-09-24 | Full-screen Zillow-style map, one pin per home at its latest sale | Garrett's call. Repeat sales go in the popup's sale history. |
| 2026-09-24 | Self-host MapLibre; CARTO and Esri basemaps; HTML price pins | No CDN, account or font dependency. Keyless basemaps. |
| 2026-09-24 | QC pass: shared `common.js`, single `config.py`, pinned deps, Node 24 actions, publish guard, smoke test | So new features build on one structure instead of copies. |

## Open questions

- Should the map's price filter use today's dollars when the dashboard is in "Today's $"? The map currently always uses nominal prices; the dashboard follows its toggle.
- Is it worth moving `data/raw/` out of git (for example, into a release asset) to keep the repo small long-term? Not needed yet.
