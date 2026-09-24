"""Pull Denver single-family sales for 13 target neighborhoods from the city's ArcGIS REST API.

Runs in GitHub Actions (Denver's servers are reachable there). Writes gzipped CSVs to data/raw/.

Sources (all City and County of Denver open data):
  - Statistical neighborhood polygons  -> official 78-neighborhood boundaries
  - Parcels (single-family only)       -> address, zoning, situs coordinates
  - Residential characteristics        -> beds, baths, sqft, year built
  - Real property sales and transfers  -> every deed, 2015+ (the API holds nothing earlier)

Each parcel is placed in a statistical neighborhood by point-in-polygon on its situs coordinates.
Buyer/seller names are reduced to flags before anything is written; no personal names are committed.
Denver reloads some tables nightly; if any table looks partially loaded, the run fails and the
previous week's data is kept.
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from shapely.geometry import Point, Polygon
from shapely.prepared import prep

BASE = "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services"
SALES = f"{BASE}/ODC_real_property_sales_and_transfers/FeatureServer/60/query"
RESCHAR = f"{BASE}/ODC_real_property_residential_characteristics/FeatureServer/59/query"
PARCELS = f"{BASE}/ODC_PROP_PARCELS_A/FeatureServer/245/query"
NBHDS = f"{BASE}/ODC_ADMN_NEIGHBORHOOD_A/FeatureServer/13/query"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"
PAGE = 2000
STATE_PLANE = 2232  # NAD83 / Colorado Central (ftUS), the SR of SITUS_X/Y_COORD

TARGETS = {
    # statistical neighborhood name -> cluster
    "Berkeley": "Northwest", "Sunnyside": "Northwest", "West Highland": "Northwest",
    "Highland": "Northwest", "Sloan Lake": "Northwest",
    "Washington Park West": "Southeast", "Washington Park": "Southeast", "Platt Park": "Southeast",
    "University": "Southeast", "University Park": "Southeast", "Cory - Merrill": "Southeast",
    "Belcaro": "Southeast", "Cheesman Park": "Southeast",
}

# Minimum plausible row counts; below these a table is mid-reload.
MIN_ROWS = {"parcels_sfr": 100_000, "residential": 150_000, "sales_citywide": 100_000}

S = requests.Session()
S.headers["User-Agent"] = "denver-neighborhood-dashboard (personal research)"


def get(url: str, params: dict) -> dict:
    for attempt in range(5):
        try:
            r = S.get(url, params=params, timeout=120)
            r.raise_for_status()
            js = r.json()
            if "error" in js:
                raise RuntimeError(js["error"])
            return js
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise
            print(f"  retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))


def count(url: str, where: str) -> int:
    return get(url, {"where": where, "returnCountOnly": "true", "f": "json"})["count"]


def fetch_all(url: str, where: str, fields: str) -> pd.DataFrame:
    """Keyset pagination on OBJECTID."""
    rows, last_id = [], -1
    if fields != "*" and "OBJECTID" not in fields.split(","):
        fields = "OBJECTID," + fields
    name = url.split("/")[-4]
    while True:
        js = get(url, {"where": f"({where}) AND OBJECTID>{last_id}", "outFields": fields,
                       "orderByFields": "OBJECTID", "resultRecordCount": PAGE,
                       "returnGeometry": "false", "f": "json"})
        feats = js.get("features", [])
        if not feats:
            break
        rows.extend(f["attributes"] for f in feats)
        last_id = max(f["attributes"]["OBJECTID"] for f in feats)
        if len(rows) % 20000 < PAGE:
            print(f"  {name}: {len(rows):,} rows", flush=True)
    print(f"  {name}: {len(rows):,} rows total", flush=True)
    return pd.DataFrame(rows)


def guard(label: str, n: int):
    if n < MIN_ROWS[label]:
        sys.exit(f"ABORT: {label} has {n:,} rows (< {MIN_ROWS[label]:,}); Denver is likely mid-reload. "
                 "Keeping previous data.")


def neighborhoods() -> dict:
    js = get(NBHDS, {"where": "1=1", "outFields": "NBHD_NAME", "returnGeometry": "true",
                     "outSR": STATE_PLANE, "f": "json"})
    polys = {}
    for f in js["features"]:
        rings = f["geometry"]["rings"]
        # Esri rings: outer rings clockwise, holes counter-clockwise. Build outer + holes.
        outers, holes = [], []
        for ring in rings:
            p = Polygon(ring)
            (holes if p.exterior.is_ccw else outers).append(p)
        shape = outers[0]
        for o in outers[1:]:
            shape = shape.union(o)
        for h in holes:
            shape = shape.difference(h)
        polys[f["attributes"]["NBHD_NAME"]] = shape
    return polys


def parid(x) -> int | None:
    try:
        return int(float(str(x).strip()))
    except ValueError:
        return None


ENTITY = re.compile(r"\b(LLC|INC|CORP|CO|LP|LLP|TRUST|TRUSTEE|BANK|HOMES|PROPERTIES|HOLDINGS|INVEST\w*|"
                    r"PARTNERS\w*|FUND|CAPITAL|REALTY|VENTURES|ASSOCIATION|MORTGAGE|FEDERAL|HUD|ESTATE)\b")


def last_names(s) -> set:
    if not isinstance(s, str):
        return set()
    return {p.split(",")[0].strip() for p in s.split("&") if "," in p}


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Pre-flight: bail before downloading anything if a table is mid-reload.
    guard("residential", count(RESCHAR, "1=1"))
    guard("sales_citywide", count(SALES, "CLASS='R'"))
    guard("parcels_sfr", count(PARCELS, "D_CLASS_CN LIKE 'SFR%'"))

    print("Neighborhood boundaries…")
    polys = neighborhoods()
    missing = set(TARGETS) - set(polys)
    if missing:
        sys.exit(f"ABORT: neighborhoods not found: {missing}")

    print("Single-family parcels…")
    pc = fetch_all(PARCELS, "D_CLASS_CN LIKE 'SFR%'",
                   "SCHEDNUM,SITUS_ADDRESS_LINE1,SITUS_ZIP,SITUS_X_COORD,SITUS_Y_COORD,ZONE_10,"
                   "LAND_AREA,RES_ORIG_YEAR_BUILT,RES_ABOVE_GRADE_AREA,D_CLASS_CN")
    guard("parcels_sfr", len(pc))

    # Assign every SFR parcel to a statistical neighborhood (all 78, to validate the join).
    prepared = {k: prep(v) for k, v in polys.items()}
    bboxes = {k: v.bounds for k, v in polys.items()}

    def locate(x, y):
        if pd.isna(x) or pd.isna(y):
            return None
        pt = Point(x, y)
        for k, (x0, y0, x1, y1) in bboxes.items():
            if x0 <= x <= x1 and y0 <= y <= y1 and prepared[k].contains(pt):
                return k
        return None

    pc["STAT_NBHD"] = [locate(x, y) for x, y in zip(pc.SITUS_X_COORD, pc.SITUS_Y_COORD)]
    hit = pc.STAT_NBHD.notna().mean()
    print(f"  parcels placed in a neighborhood: {hit:.1%}")
    if hit < 0.95:
        sys.exit(f"ABORT: only {hit:.1%} of parcels matched a neighborhood; coordinate system mismatch?")
    pc = pc[pc.STAT_NBHD.isin(TARGETS)].copy()
    pc["CLUSTER"] = pc.STAT_NBHD.map(TARGETS)
    pc["PARID"] = pc.SCHEDNUM.map(parid)
    print(pc.STAT_NBHD.value_counts().to_string())
    keep = set(pc.PARID.dropna())

    print("Residential characteristics…")
    rc = fetch_all(RESCHAR, "1=1", "PARID,BED_RMS,FULL_B,HLF_B,AREA_ABG,BSMT_AREA,FBSMT_SQFT,STORY,"
                                    "STYLE_CN,CCYRBLT,LAND_SQFT,ZONE10,D_CLASS_CN,UNITS,TOTAL_VALUE")
    guard("residential", len(rc))
    rc["PARID"] = rc.PARID.map(parid)
    rc = rc[rc.PARID.isin(keep)]

    print("Sales…")
    sales = fetch_all(SALES, "CLASS='R'", "*")
    guard("sales_citywide", len(sales))
    sales["PARID"] = sales.PARID.map(parid)
    sales = sales[sales.PARID.isin(keep)].copy()
    g, b = sales["GRANTOR"].fillna(""), sales["GRANTEE"].fillna("")
    sales["SELLER_ENTITY"] = g.str.upper().str.contains(ENTITY)
    sales["BUYER_ENTITY"] = b.str.upper().str.contains(ENTITY)
    sales["SAME_PARTY"] = [bool(last_names(x) & last_names(y)) for x, y in zip(g, b)]
    sales = sales.drop(columns=["GRANTOR", "GRANTEE"])

    # Write only after every table passed its checks.
    pc.drop(columns=["OBJECTID"]).to_csv(OUT / "parcels.csv.gz", index=False)
    rc.drop(columns=["OBJECTID"]).to_csv(OUT / "residential.csv.gz", index=False)
    sales.to_csv(OUT / "sales.csv.gz", index=False)
    print(f"Done: {len(pc):,} parcels, {len(rc):,} residential records, {len(sales):,} sales "
          "in the 13 target neighborhoods")


if __name__ == "__main__":
    main()
