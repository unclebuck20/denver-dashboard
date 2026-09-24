"""Pull Denver assessor sales + residential characteristics from the city's ArcGIS REST API.

Runs in GitHub Actions (Denver's servers are reachable there). Writes gzipped CSVs to data/raw/.
Buyer/seller names are reduced to flags before anything is written, so no personal names are committed.
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services"
SALES = f"{BASE}/ODC_real_property_sales_and_transfers/FeatureServer/60/query"
RESCHAR = f"{BASE}/ODC_real_property_residential_characteristics/FeatureServer/59/query"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"
PAGE = 2000


def fetch_all(url: str, where: str, fields: str) -> pd.DataFrame:
    rows, offset = [], 0
    s = requests.Session()
    s.headers["User-Agent"] = "denver-neighborhood-dashboard (personal research)"
    while True:
        params = {
            "where": where, "outFields": fields, "orderByFields": "OBJECTID",
            "resultOffset": offset, "resultRecordCount": PAGE, "f": "json",
        }
        for attempt in range(5):
            try:
                r = s.get(url, params=params, timeout=90)
                r.raise_for_status()
                js = r.json()
                if "error" in js:
                    raise RuntimeError(js["error"])
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 4:
                    raise
                print(f"  retry {attempt + 1} at offset {offset}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        feats = js.get("features", [])
        rows.extend(f["attributes"] for f in feats)
        print(f"  {url.split('/')[-4]}: {len(rows):,} rows", flush=True)
        if not feats or not js.get("exceededTransferLimit", len(feats) == PAGE):
            break
        offset += len(feats)
    return pd.DataFrame(rows)


ENTITY = re.compile(r"\b(LLC|INC|CORP|CO|LP|LLP|TRUST|TRUSTEE|BANK|HOMES|PROPERTIES|HOLDINGS|INVEST\w*|"
                    r"PARTNERS\w*|FUND|CAPITAL|REALTY|VENTURES|ASSOCIATION|MORTGAGE|FEDERAL|HUD|ESTATE)\b")


def last_names(s) -> set:
    if not isinstance(s, str):
        return set()
    return {p.split(",")[0].strip() for p in s.split("&") if "," in p}


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print("Sales (single-family class R, 2008+)…")
    sales = fetch_all(SALES, "CLASS='R' AND SALE_YEAR>=2008", "*")
    g, b = sales["GRANTOR"].fillna(""), sales["GRANTEE"].fillna("")
    sales["SELLER_ENTITY"] = g.str.upper().str.contains(ENTITY)
    sales["BUYER_ENTITY"] = b.str.upper().str.contains(ENTITY)
    sales["SAME_PARTY"] = [bool(last_names(x) & last_names(y)) for x, y in zip(g, b)]
    sales = sales.drop(columns=["GRANTOR", "GRANTEE"])
    sales.to_csv(OUT / "sales.csv.gz", index=False)

    print("Residential characteristics…")
    fields = ("PARID,NBHD_1,NBHD_1_CN,D_CLASS_CN,PROP_CLASS,ZONE10,LAND_SQFT,AREA_ABG,BSMT_AREA,"
              "FBSMT_SQFT,STORY,STYLE_CN,BED_RMS,FULL_B,HLF_B,CCYRBLT,UNITS,TOTAL_VALUE,"
              "SITE_NBR,SITE_DIR,SITE_NAME,SITE_MODE")
    rc = fetch_all(RESCHAR, "1=1", fields)
    rc.to_csv(OUT / "residential.csv.gz", index=False)

    print(f"Done: {len(sales):,} sales, {len(rc):,} residential parcels")


if __name__ == "__main__":
    main()
