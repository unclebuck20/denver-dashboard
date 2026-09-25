# Data Product Starter

*Drop this file into a fresh Claude chat, then say what you want to track, for example: "Use this to build a tracker for ___."*

---

## What we're building

A small, durable **data product**: a public data source flows through a weekly pipeline, gets cleaned and shaped with judgment about what matters, and lands on a live web page Garrett can use to make a decision. The first one was the Denver Neighborhood Sales dashboard (github.com/unclebuck20/denver-dashboard). It started from Denver's property-sales API and ended as a dashboard plus a Zillow-style map, refreshed every Monday for $0.

Every product in this family has the same five layers:

| Layer | What it is | Default choice |
|---|---|---|
| 1. **Operating base** | A Claude Project holding the instructions and handbook | Project instructions plus a `handbook/` folder uploaded as knowledge |
| 2. **Repo** | Code, data snapshots, docs; the source of truth | Public GitHub repo (private if the data is sensitive) |
| 3. **Data flow** | Scheduled pull from an API or feed | GitHub Actions cron → `scripts/fetch.py` → `data/raw/` |
| 4. **Processing** | Cleaning, joining, derived fields, the "so what" | `scripts/build.py` → one JSON file with a documented contract |
| 5. **Page** | What Garrett actually looks at | Static HTML/JS on GitHub Pages, reading that JSON |

The pattern stays fixed; the source, the processing, and the page change each time.

## How Claude should run the build

Garrett directs; Claude builds. **Confirm scope before anything substantial**, then execute and stop.

**Step 0: Frame (one short exchange).** Pin down four things:
- What decision or habit will this serve?
- What's the smallest version worth using weekly?
- Which source(s)?
- What does the page need to answer at a glance?

Propose answers; don't interview.

**Step 1: Source recon (before any code).** For each candidate source, find:
- the endpoint
- auth needs (a key, and whether it can stay server-side)
- rate limits and page size
- row counts
- how far back history goes
- how often it updates
- the licence or terms

Use web fetch or small queries for discovery only. Sandboxes usually can't reach arbitrary hosts; GitHub Actions can. Report surprises (missing history, broken fields) before building on them.

**Step 2: First pull in Actions.** Stand up the repo and workflow, then pull a real slice. Profile it:
- what's clean and what's junk
- nulls and outliers
- what keys join the tables

**Step 3: Processing and data contract.** Write the cleaning rules as a numbered funnel with counts at each step. Define the JSON the page reads: `meta` (built time, freshness, the funnel, modes), a `columns` list, and rows as arrays. Pages look columns up by name. Keep names and secrets out.

**Step 4: Page.** Answer the core question above the fold. Show the raw records, not just aggregates. Filters go in one row above the content. Every chart gets a table view. Support light and dark modes and phone width, and link out to the source of each record.

**Step 5: Harden.**
- Guards that fail closed: minimum row counts, match rates, and a no-big-drop check before publishing.
- Pinned `requirements.txt` and a concurrency group on the workflow.
- A browser smoke test.
- The handbook: `PROJECT_INSTRUCTIONS`, `ARCHITECTURE`, `DATA`, `OPERATIONS`, `ROADMAP`.

**Step 6: Operating base.** Garrett creates the Claude Project, pastes `PROJECT_INSTRUCTIONS.md`, and uploads the handbook as knowledge.

## Garrett's setup checklist (about 10 minutes, once per product)

1. Create an empty GitHub repo (no README). Public unless the data is private.
2. Give Claude write access, either way:
   - **Best:** connect GitHub to Claude and attach the repo to the session, so Claude can push directly.
   - **Otherwise:** a fine-grained token for that repo only: Contents RW, Workflows RW, Actions RW (Metadata R is automatic), with a 30-day expiry. Plus the Claude desktop app open with `~/projects` connected, since pushes go through the Mac.
3. After the first successful run: Settings → Pages → Deploy from a branch → `main` / `/docs`.
4. Any API keys go in **Settings → Secrets and variables → Actions**, never in the page. A static page is public, so anything that needs a key runs in the Action.

## Templates that carry over

```
repo/
  .github/workflows/refresh.yml   # cron + dispatch + push-on-code; concurrency group; pinned ubuntu; commit only if changed
  scripts/config.py               # what's covered (the one place to change scope)
  scripts/fetch.py                # pull → guards → data/raw/   (report via ::notice:: / ::error:: annotations)
  scripts/build.py                # clean → funnel → docs/data.json   (publish guard vs. previous build)
  data/raw/                       # committed snapshots so build.py runs offline
  docs/index.html, docs/js/common.js, docs/vendor/   # static page(s), shared helpers, self-hosted libraries
  tests/smoke_test.py             # Playwright checks: renders, filters work, no JS errors, no sideways scroll
  handbook/                       # the five docs
  requirements.txt
```

Patterns worth reusing verbatim from the Denver repo:
- **Keyset pagination** (`WHERE id > last_id ORDER BY id`) instead of offset paging.
- A **pre-flight count** on each source before downloading.
- **Guards that `exit 1` before writing anything**, so a bad week leaves last week's data live.
- **Annotations for run results.** Sandboxes usually can't download Actions logs, but can read annotations through the API.
- **Privacy scrubbing in fetch.** Reduce personal names to flags before they touch disk.
- **Shared page helpers** in one `common.js`, and a single `localStorage` key merged on save so multiple pages share filters.
- **Map stack when needed:** self-hosted MapLibre, CARTO Voyager / Dark Matter plus Esri satellite (keyless), HTML markers for labels and pins, and a fallback to a blank style if tiles fail.

## Gotchas already paid for

- Claude's cloud sandbox blocks most outside hosts, including GitHub pushes to repos not attached to the session. **Fetch in Actions; push through an attached repo or the Mac.**
- Public-data tables get reloaded or truncated without notice (Denver's bed/bath table was 90% missing for two months). Always check counts and fail closed.
- Catalog descriptions lie about history ("2008 to present" meant 2015). Verify date ranges with a query.
- Two sources' "neighborhood" or "category" fields rarely match. Join on geometry or an official key.
- Attributes are often the current state, not the state at event time (house size today vs. at sale). Say so on the page.
- When copying files to the Mac, a reused staged filename once pushed a stale copy. Ship **git bundles**, or verify `md5sum` on both ends.
- Git on the Mac needs delete permission in the connected folder, for lock files. Grant it once per session.
- Never commit a locally built data file from a sandbox that lacked a source (CPI was missing locally). Let the Action build what ships.

## Idea bank: source → processing → outcome

Chosen to feed Garrett's live priorities. Size: S (a weekend), M (a few sessions), L (needs paid data or heavy modeling).

| Idea | Source(s) | Processing | Page / outcome | Size |
|---|---|---|---|---|
| **Thesis tracker** for the individual-stock sleeve | SEC EDGAR (8-K, 10-Q/10-K, Form 4, 13F), free with a User-Agent | Diff risk factors quarter over quarter, flag thesis-break language, insider buys vs. sales | A green/yellow/red card per holding with filing evidence and links; "no action" is the default | M |
| **Rate and affordability board** for the Denver purchase | FRED (30-yr mortgage, 10-yr, CPI), plus this repo's sales | Monthly payment at the median 3/2 price per neighborhood; how much rate changes move it | "What $X buys in each neighborhood at today's rate", with a what-if slider | S |
| **Song gap and show tracker** for The Wire | phish.net API (key), setlist.fm API (key), Internet Archive LMA | Gaps, bust-out probabilities, debut and rotation stats per tour | Pre-show "likely songs" page; post-show recap cards | M |
| **MiLB breakout board** | MLB Stats API (free) | Rolling K%/BB%/ISO vs. level, age-relative performance, promotion velocity | Prospects heating up before rankings move; card links | M |
| **Build and ADU pressure map** | Denver (and Seattle) building permits open data | Permits by type per block, joined to parcels and sales | Where scrapes, additions and ADUs are clustering | M |
| **Third-place site scout** | Colorado liquor licenses, Denver business licenses, Census ACS, parcels/zoning | Density of bars/cafés/venues vs. population and income; vacancy signals | Candidate-block map for the venue concept | M |
| **Powder and trip alerts** | NOAA / NWS API (free), CAIC avalanche forecasts | Storm totals by resort region, forecast deltas | Weekly "where to ski" card plus alerts | S |
| **Legal-AI market radar** (Supio edge) | CourtListener API, Federal Register, company news | PI verdict trends, rules touching legal AI, competitor moves | Weekly brief page for work | M |
| **AI adoption radar** | arXiv, Hugging Face trending, GitHub releases, Hacker News | Cluster topics, spot fast risers, dedupe hype | "What moved this week" with links | S–M |

## Kickoff message to paste after this file

> Using the Data Product Starter above: I want to build **[idea]** so I can **[decision or habit it serves]**. Source(s) I have in mind: **[sources, or "recommend"]**. Start with Step 0: propose the scope, the smallest useful version, and what the page answers at a glance. Wait for my go before building.
