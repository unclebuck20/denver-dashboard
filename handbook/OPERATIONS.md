# Operations

How the dashboard stays fresh, how to ship a change, and what to do when something breaks.

## Weekly refresh (automatic)

- **When:** Mondays 13:00 UTC (6am Pacific in summer, 5am in winter), plus any push that touches `scripts/`, `requirements.txt`, `docs/index.html`, `docs/map.html`, `docs/js/`, or the workflow file. It can also be started by hand from the repo's **Actions → Weekly data refresh → Run workflow**.
- **What it does:** installs pinned packages → `fetch.py` → `build.py` → commits `data/` and `docs/` as `data-bot` if anything changed → GitHub Pages republishes `docs/` within about a minute.
- **Safety:** a concurrency group stops two runs from racing. Guards stop the run *before* anything is committed, so the live site keeps last week's data:
  - `fetch.py`: a source table below its minimum rows (parcels 100k, citywide sales 100k), or under 95% of parcels matching a neighborhood, or a configured neighborhood name not found.
  - `build.py`: clean sales fell more than 10% from what's live, or a column disappeared.
- **Where to look:** each run posts notices (parcel counts per neighborhood, residential completeness, totals) and any `ABORT` reason as annotations on the run. Garrett gets GitHub's standard email when a scheduled run fails.

## Shipping a change (how Claude works on this)

1. **Sync:** `git clone https://github.com/unclebuck20/denver-dashboard.git`, or `git pull` an existing copy. The data bot commits weekly and after every code push.
2. **Edit** the right layer (see `ARCHITECTURE.md`). Coverage changes go in `scripts/config.py` only.
3. **Rebuild locally:** `pip install -r requirements.txt && python scripts/build.py`. This works offline from the committed `data/raw/`. FRED is often unreachable from sandboxes, which only disables the "Today's $" toggle locally. **Don't commit a locally built `docs/data.json`**; let the Action build it (`git checkout docs/data.json docs/neighborhoods.geojson` before committing).
4. **Test:** `python tests/smoke_test.py` must print "All checks passed." For visual changes, also screenshot light, dark, and 390px-wide views.
5. **Push** (see the next section for how), then **watch the run** until it succeeds and read its notices. Pages deploys right after. Only then call it live.

### Push paths

A Claude cloud workspace can clone this public repo but **can't push to it** unless the repo is attached to the session. Two ways to ship:

- **A. Preferred: connect GitHub to Claude** and attach `unclebuck20/denver-dashboard` when starting a session. Claude can then push directly. The proxy's own error message says: "add the repository to the session's sources."
- **B. Current path: through Garrett's Mac.** With the Claude desktop app open and `~/projects` connected:
  1. Commit in the cloud workspace, then `git bundle create <outputs>/change.bundle origin/main..main`.
  2. Copy the bundle to `~/projects/` on the Mac (device file copy), then in the Mac shell: `git fetch <remote> main && git reset --hard FETCH_HEAD`, `git fetch ../change.bundle main:tmp && git merge --ff-only tmp`, and delete the bundle.
  3. Push with the token inline in the URL (`https://x-access-token:$TOKEN@github.com/...`). Never write it into `.git/config` or a file.
  4. Git needs delete permission on `~/projects` for its lock files. Grant it once per session when asked.
  - **Lesson learned:** copying individual files to the Mac once pushed a *stale* file with the same staged name. Bundles avoid this. If you must copy files, use new staged filenames each time and compare `md5sum` on both sides before committing.

### GitHub token (path B)

- Fine-grained token **"Denver Real Estate,"** scoped to this repo only: Contents RW, Workflows RW, Actions RW, Metadata R. **Expires Oct 23, 2026.**
- Actions RW lets Claude start runs and read run results. Log downloads are blocked from the sandboxes, which is why the scripts report through `::notice::` and `::error::` annotations.
- The token has been pasted in chat. **Regenerate it** (github.com/settings/personal-access-tokens → Regenerate) when this phase of work wraps, and definitely before sharing the chat. Delete it once path A is set up.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Run failed with `ABORT: <table> has N rows` | Denver is mid-reload or truncated a table | Nothing breaks; last week's data stays live. Re-run later. If it persists for days, check the table's `returnCountOnly` and `editingInfo.lastEditDate` (see `DATA.md`). |
| Run failed at `build.py` with "Clean sales fell…" | A partial source or a cleaning change dropped rows | Compare the fetch notices to the last good run. If the drop is real and intended, delete `docs/data.json` in the same commit to reset the baseline. |
| Dashboard says "Bedroom and bathroom counts aren't available" | Residential table incomplete → sq-ft proxy mode | Automatic; it clears when Denver restores the table. |
| "Today's $" greyed out | FRED unreachable during the build | Next run usually fixes it. |
| Map shows pins but no streets | CARTO or Esri tile outage, or a network block | The page falls back to a plain background. Try Satellite; swap the style URL in `map.html` if it's persistent. |
| Page didn't update after a push | Pages deploy still running, or the browser cache | Check Actions for "pages build and deployment"; hard-refresh. |
| `git push` rejected (non-fast-forward) | The data bot committed in between | `git pull --rebase` and push again. |
| Push 403 "not in this session's authorized repository set" | Cloud workspace without the repo attached | Use path A or B above. |

## Costs and limits

Everything is free: public-repo Actions minutes (about 3 minutes per run), GitHub Pages, Denver open data, FRED, CARTO and Esri basemaps (attributed, personal use). `docs/data.json` is about 2.7 MB (Pages compresses it). The repo grows roughly 0.5–1 MB per weekly data commit; revisit (e.g., stop committing `data/raw/`) if it passes about 500 MB.
