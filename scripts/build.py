"""Clean raw Denver sales into arm's-length single-family sales and write docs/data.json for the dashboard.

Cleaning rules (each is counted in data.json -> meta.cleaning so the dashboard can show them):
  1. Deed type is a market conveyance: WD (warranty), SW (special warranty), GW (general warranty),
     PR (personal representative / estate sale). Quitclaims, death certificates, bargain-and-sale,
     trustee and similar transfers are dropped.
  2. Price >= $100,000 (drops nominal $0/$10 consideration and partial-interest transfers).
  3. Buyer and seller do not share a last name (family transfers).
  4. The deed conveys exactly one parcel (multi-parcel portfolio deals have no per-home price).
  5. The house standing today existed at the time of sale (year built <= sale year). Otherwise the
     sale was of an older house or a teardown, and today's square footage doesn't describe it.
  6. $/sq ft between $75 and $2,500 (data-entry errors).
The 3 bed / 2 bath requirement is applied in the dashboard: by true beds/baths when Denver's residential
table is complete, otherwise by an above-grade square-footage threshold the viewer can adjust.
"""
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DOCS = ROOT / "docs"

NEIGHBORHOODS = [  # display order: Northwest, Central, Southeast
    ("Berkeley", "Northwest"), ("Sunnyside", "Northwest"), ("West Highland", "Northwest"),
    ("Highland", "Northwest"), ("Sloan Lake", "Northwest"),
    ("City Park West", "Central"), ("City Park", "Central"), ("Congress Park", "Central"),
    ("Cheesman Park", "Central"), ("Cherry Creek", "Central"),
    ("Washington Park West", "Southeast"), ("Washington Park", "Southeast"), ("Platt Park", "Southeast"),
    ("University", "Southeast"), ("University Park", "Southeast"), ("Cory - Merrill", "Southeast"),
    ("Belcaro", "Southeast"),
]
DISPLAY = {"Cory - Merrill": "Cory-Merrill"}
MARKET_DEEDS = {"WD", "SW", "GW", "PR"}


def cpi() -> dict | None:
    """Monthly US CPI-U (FRED CPIAUCSL) as {'YYYY-MM': value}; None if unreachable."""
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "cpi"]
        df = df[pd.to_numeric(df.cpi, errors="coerce").notna()]
        df = df[df.date >= "2014-12-01"]
        return {d[:7]: round(float(v), 3) for d, v in zip(df.date, df.cpi)}
    except Exception as e:  # noqa: BLE001
        print(f"CPI unavailable: {e}")
        return None


def sale_date(year, monthday) -> date | None:
    try:
        md = int(monthday)
        return date(int(year), md // 100, md % 100)
    except (ValueError, TypeError):
        return None


def main():
    sales = pd.read_csv(RAW / "sales.csv.gz")
    parcels = pd.read_csv(RAW / "parcels.csv.gz")
    res_path = RAW / "residential.csv.gz"
    residential = pd.read_csv(res_path, low_memory=False) if res_path.exists() else None

    steps = [("Deeds and transfers on target single-family parcels (2015+)", len(sales))]

    receptions_per = sales.groupby("RECEPTION_NUM").PARID.nunique()
    multi = set(receptions_per[receptions_per > 1].index)

    s = sales[sales.INSTRUMENT.isin(MARKET_DEEDS)]
    steps.append(("Market deed types (warranty, special warranty, estate)", len(s)))
    s = s[s.SALE_PRICE >= 100_000]
    steps.append(("Price at least $100,000", len(s)))
    s = s[~s.SAME_PARTY]
    steps.append(("Buyer and seller not related by name", len(s)))
    s = s[~s.RECEPTION_NUM.isin(multi)]
    steps.append(("Single-parcel deeds", len(s)))

    # Parcel situs coordinates are Colorado Central state plane (ftUS); the map needs lat/lon.
    to_ll = Transformer.from_crs(2232, 4326, always_xy=True)
    lon, lat = to_ll.transform(parcels.SITUS_X_COORD.values, parcels.SITUS_Y_COORD.values)
    parcels = parcels.assign(LAT=lat.round(5), LON=lon.round(5))
    s = s.merge(parcels[["PARID", "STAT_NBHD", "SITUS_ADDRESS_LINE1", "SITUS_ZIP", "ZONE_10", "LAND_AREA",
                         "RES_ORIG_YEAR_BUILT", "RES_ABOVE_GRADE_AREA", "LAT", "LON"]], on="PARID", how="inner")
    s = s[s.RES_ORIG_YEAR_BUILT.notna() & (s.RES_ORIG_YEAR_BUILT <= s.SALE_YEAR)]
    steps.append(("Current house existed at time of sale", len(s)))
    s = s[s.RES_ABOVE_GRADE_AREA > 0]
    s["PPSF"] = s.SALE_PRICE / s.RES_ABOVE_GRADE_AREA
    s = s[s.PPSF.between(75, 2500)]
    steps.append(("Plausible price per sq ft", len(s)))

    s["DATE"] = [sale_date(y, md) for y, md in zip(s.SALE_YEAR, s.SALE_MONTHDAY)]
    s = s[s.DATE.notna()]
    s["RECORDED"] = pd.to_datetime(s.RECEPTION_DATE.astype("Int64").astype(str), format="%Y%m%d",
                                   errors="coerce")
    # A sale can't close after its deed was recorded; when it appears to, the month/day was keyed wrong.
    late = s.RECORDED.notna() & (pd.to_datetime(s.DATE) > s.RECORDED)
    s.loc[late, "DATE"] = s.loc[late, "RECORDED"].dt.date

    beds_mode = "sqft"
    if residential is not None:
        residential = residential.drop_duplicates("PARID")
        s = s.merge(residential[["PARID", "BED_RMS", "FULL_B", "HLF_B"]], on="PARID", how="left")
        beds_mode = "beds"

    nb_index = {name: i for i, (name, _) in enumerate(NEIGHBORHOODS)}
    s = s[s.STAT_NBHD.isin(nb_index)].sort_values("DATE")

    rows = []
    for r in s.itertuples():
        row = [
            r.DATE.isoformat(),
            nb_index[r.STAT_NBHD],
            int(r.SALE_PRICE),
            int(r.RES_ABOVE_GRADE_AREA),
            int(r.RES_ORIG_YEAR_BUILT),
            int(r.LAND_AREA) if pd.notna(r.LAND_AREA) else None,
            r.ZONE_10 if isinstance(r.ZONE_10, str) else "",
            " ".join(w.lower() if w[:1].isdigit() else w.capitalize() for w in r.SITUS_ADDRESS_LINE1.split())
            if isinstance(r.SITUS_ADDRESS_LINE1, str) else "",
            r.RECORDED.date().isoformat() if pd.notna(r.RECORDED) else None,
        ]
        if beds_mode == "beds":
            baths = (r.FULL_B or 0) + 0.5 * (r.HLF_B or 0)
            row += [None if pd.isna(r.BED_RMS) else int(r.BED_RMS), None if pd.isna(baths) else baths]
        row.append(str(r.SITUS_ZIP)[:5] if isinstance(r.SITUS_ZIP, str) else "")
        row += [int(r.PARID), None if pd.isna(r.LAT) else float(r.LAT), None if pd.isna(r.LON) else float(r.LON)]
        rows.append(row)

    out = {
        "meta": {
            "built": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "latest_recorded": s.RECORDED.max().date().isoformat() if s.RECORDED.notna().any() else None,
            "beds_mode": beds_mode,
            "default_min_sqft": 0 if beds_mode == "beds" else 1400,
            "cleaning": [{"step": k, "rows": int(v)} for k, v in steps],
            "neighborhoods": [{"name": DISPLAY.get(n, n), "cluster": c,
                               "parcels": int((parcels.STAT_NBHD == n).sum())} for n, c in NEIGHBORHOODS],
            "columns": ["date", "nbhd", "price", "sqft", "year_built", "lot_sqft", "zone", "address",
                        "recorded"] + (["beds", "baths"] if beds_mode == "beds" else []) + ["zip", "pid", "lat", "lon"],
        },
        "cpi": cpi(),
        "sales": rows,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data.json").write_text(json.dumps(out, separators=(",", ":")))
    boundaries = RAW / "neighborhoods.geojson"
    if boundaries.exists():
        gj = json.loads(boundaries.read_text())
        feats = []
        for f in gj["features"]:
            g = shape(f["geometry"]).simplify(0.00003, preserve_topology=True)
            geom = json.loads(json.dumps(mapping(g)), parse_float=lambda v: round(float(v), 5))
            name = f["properties"]["NBHD_NAME"]
            feats.append({"type": "Feature", "properties": {"name": DISPLAY.get(name, name)}, "geometry": geom})
        (DOCS / "neighborhoods.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                               separators=(",", ":")))
    for k, v in steps:
        print(f"{v:>7,}  {k}")
    print(f"Wrote {len(rows):,} clean sales (beds mode: {beds_mode})")


if __name__ == "__main__":
    main()
