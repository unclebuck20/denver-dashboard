# Data

Where every number comes from, how it's cleaned, and the city-data quirks that have already bitten us.

## Sources

All Denver tables come from the City and County of Denver Open Data Catalog, served as ArcGIS hosted feature services under
`https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/`. No key is needed. The page size is 2,000 rows.

| Table | Service / layer | What we use | Notes |
|---|---|---|---|
| Real property sales and transfers | `ODC_real_property_sales_and_transfers/FeatureServer/60` | Every deed on single-family parcels (`CLASS='R'`): price, sale year/month-day, recording date, deed type, buyer/seller (reduced to flags) | **Holds 2015+ only**, despite the catalog saying 2008/2010. |
| Residential characteristics | `ODC_real_property_residential_characteristics/FeatureServer/59` | Bedrooms, full/half baths, above-grade sq ft, year built | Describes the house **today**, not at the time of sale. Was truncated Jul 25–Sep 24, 2026 (see quirks). |
| Parcels | `ODC_PROP_PARCELS_A/FeatureServer/245` | Address, zip, zoning, lot size, year built, above-grade sq ft, situs coordinates | Coordinates are Colorado Central state plane, ft (EPSG:2232). |
| Statistical neighborhoods | `ODC_ADMN_NEIGHBORHOOD_A/FeatureServer/13` | The 78 official neighborhood polygons (`NBHD_NAME`) | Use these names in `config.py` exactly as written, e.g. `Cory - Merrill`. |
| FRED CPIAUCSL | `fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL` | Monthly US CPI-U for "Today's $" | No key needed. If unreachable, the toggle is disabled for that week. |

**Joins.** The parcel ID is `PARID` in sales and residential, and `SCHEDNUM` in parcels. All three are normalized to an integer. Each parcel is placed in a neighborhood by point-in-polygon on its situs coordinates, which currently matches 100% of parcels. The assessor's own `NBHD_1_CN` field is **not** the statistical neighborhood; don't use it.

## Cleaning funnel (`build.py`)

The dashboard's "How the numbers are built" section shows the live counts for each step.

1. **Market deed types only:** `WD` warranty, `SW` special warranty, `GW` general warranty, `PR` personal representative (estate). This drops quitclaims (`QC`), death certificates, bargain-and-sale, trustee deeds and the like.
2. **Price ≥ $100,000:** drops $0/$10 nominal-consideration transfers.
3. **Buyer and seller don't share a last name:** drops family transfers.
4. **The deed covers one parcel only:** multi-parcel deals have no per-home price.
5. **The current house existed at the sale** (year built ≤ sale year): drops sales of homes later torn down and rebuilt, whose size today doesn't describe what sold.
6. **$/sq ft between $75 and $2,500:** drops data-entry errors.
7. **Sale date sanity:** if the sale date is after the recording date, the month/day was mistyped, so the recording date is used.

**3 bed / 2 bath** is applied in the browser: `beds ≥ 3` and `full + 0.5 × half ≥ 2`. When Denver's bed/bath table is incomplete, `build.py` sets `beds_mode: "sqft"` and the pages fall back to a minimum-size slider (default 1,400 sq ft). The pages switch back automatically when the table recovers.

**Rolling medians** use a 3-month window, widening to 6 or 12 months for neighborhoods averaging under 4 or 1.5 qualifying sales a month (Cherry Creek, City Park). A window with fewer than 5 sales is left as a gap.

**Privacy.** Buyer and seller names never leave `fetch.py`. Only three flags are kept: `SELLER_ENTITY`, `BUYER_ENTITY` (LLC, trust, bank, etc.) and `SAME_PARTY`.

## Known quirks and past incidents

| Date | What happened | How it's handled |
|---|---|---|
| Jul 25 – Sep 24, 2026 | Denver's residential characteristics table was truncated to 18,000 rows (mostly Green Valley Ranch and Montbello), and the hub CSV export was broken the same way. | `fetch.py` detects fewer than 150k rows, keeps the partial rows, and the pages switch to the sq-ft proxy. Restored Sep 24; switched back automatically. |
| Always | Offset pagination (`resultOffset`) on these services silently stops early. | `fetch_all` pages by `OBJECTID > last_id` (keyset). |
| Always | The sales service holds nothing before 2015. | History starts in 2015. For a longer view, FHFA's zip-level price index is the candidate. |
| Always | Beds, baths and square footage describe the current house. | Rule 5 above removes teardown sales. Remodels (pop-tops, basement finishes) still show today's size against older sales, so treat older years as directional. |
| Always | Above-grade sq ft excludes basements, and many Denver bungalows have their 3rd bedroom or 2nd bath downstairs. | The label tooltip explains it. Don't use sq ft as a bed/bath proxy unless forced. |
| Always | Some sale month/day values are mistyped (e.g., a December sale recorded in March). | Cleaning rule 7. |
| Always | Zillow blocks automated access, so link targets can't be verified by Claude. | Links use Zillow's address search (`/homes/<address>_rb/`), which resolves to the home page or a map pin. |

## Coverage today

17 neighborhoods in three clusters, about 29,700 single-family parcels, 37,475 deeds, **21,057 clean sales** (11,300+ of them 3 bd / 2 ba), from 2015 to the latest weekly refresh.

- **Northwest:** Berkeley, Sunnyside, West Highland, Highland, Sloan Lake
- **Central:** City Park West, City Park, Congress Park, Cheesman Park, Cherry Creek
- **Southeast:** Washington Park West, Washington Park, Platt Park, University, University Park, Cory-Merrill, Belcaro

**Valid names for `config.py`:** all 78 official names are written to `data/raw/all_neighborhoods.txt` on every run. Copy a name from there exactly (e.g., `Cory - Merrill`, `Gateway - Green Valley Ranch`). `fetch.py` aborts if a configured name isn't found.
