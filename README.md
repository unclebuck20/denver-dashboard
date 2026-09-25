# Denver Neighborhood Sales

Every arm's-length single-family home sale since 2015 across 17 Denver neighborhoods, refreshed weekly from City and County of Denver open data.

- **Dashboard:** https://unclebuck20.github.io/denver-dashboard/
- **Map:** https://unclebuck20.github.io/denver-dashboard/map.html

## How it works

A GitHub Actions job runs every Monday. `scripts/fetch.py` pulls Denver's sales, parcels, residential characteristics and neighborhood boundaries. `scripts/build.py` cleans them into `docs/data.json`. GitHub Pages serves `docs/`. Guards stop any run that looks wrong, so last week's data stays live.

## Working on it

```bash
pip install -r requirements.txt
python scripts/build.py          # rebuild docs/data.json from the committed raw data (no network to Denver needed)
python tests/smoke_test.py       # 17 browser checks; needs: pip install playwright && playwright install chromium
```

To change which neighborhoods are covered, edit `scripts/config.py` and push. The next run pulls them.

## Handbook

| Doc | Read it for |
|---|---|
| [handbook/ARCHITECTURE.md](handbook/ARCHITECTURE.md) | How the pieces fit, the `data.json` contract, the front-end conventions |
| [handbook/DATA.md](handbook/DATA.md) | Sources, joins, the cleaning funnel, known Denver data quirks |
| [handbook/OPERATIONS.md](handbook/OPERATIONS.md) | The weekly refresh, shipping a change, troubleshooting, the token |
| [handbook/ROADMAP.md](handbook/ROADMAP.md) | Backlog and the decision log |
| [handbook/PROJECT_INSTRUCTIONS.md](handbook/PROJECT_INSTRUCTIONS.md) | Custom instructions for the Claude Project that operates this repo |

## Privacy

Buyer and seller names are reduced to yes/no flags before anything is written. The repo holds only public-record facts about properties.

Data: City and County of Denver Open Data Catalog. CPI: FRED (CPIAUCSL). Maps: MapLibre GL (BSD), CARTO, Esri.
