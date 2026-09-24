# Denver Neighborhood Sales Dashboard

Tracks single-family sales (3+ bed / 2+ bath, arm's-length) since 2008 across 13 Denver neighborhoods.

- **Source:** City and County of Denver open data (assessor sales and transfers, residential characteristics), via the ArcGIS REST API.
- **Refresh:** GitHub Actions, every Monday (`.github/workflows/refresh.yml`), or on demand from the Actions tab.
- **Privacy:** buyer and seller names are reduced to flags (entity / same-party) before any data is committed.
