/* Shared helpers for index.html (dashboard) and map.html.
 * Anything both pages need lives here so a fix lands once.
 * Exposes window.DNSD. No build step: plain script, loaded before each page's own script. */
(function () {
  const STORE_KEY = "dnsd2";     // localStorage key shared by both pages
  const PRICE_CAP = 5000000;     // top of the price slider means "no maximum"

  const el = (tag, attrs = {}, text) => {
    const e = document.createElement(tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;   // textContent only: data is never parsed as HTML
    return e;
  };
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const dark = () => matchMedia("(prefers-color-scheme: dark)").matches;

  const fmt$ = v => v == null || !isFinite(v) ? "–" : "$" + Math.round(v).toLocaleString("en-US");
  const fmtK = v => v == null ? "–" : v >= 1e6 ? "$" + (v / 1e6).toFixed(v >= 1e7 ? 1 : 2) + "M" : "$" + Math.round(v / 1e3) + "K";
  const fmtPct = v => v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + (v * 100).toFixed(1) + "%";
  const fmtD = v => v ? new Date(v + "T12:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "–";
  const slug = n => n.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const median = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const addMonths = (ym, k) => {
    let [y, m] = ym.split("-").map(Number); m += k; y += Math.floor((m - 1) / 12); m = ((m - 1) % 12 + 12) % 12 + 1;
    return `${y}-${String(m).padStart(2, "0")}`;
  };

  // Zillow resolves an address-search URL to the home's page (or a map pin when it can't match one).
  const zillow = s => "https://www.zillow.com/homes/" +
    encodeURIComponent(`${s.addr}, Denver, CO${s.zip ? " " + s.zip : ""}`.replace(/,/g, "").replace(/\s+/g, "-")).replace(/%2D/g, "-") + "_rb/";

  /* Load docs/data.json and turn its column-array rows into objects.
   * Columns are looked up by name (meta.columns), so adding a column never breaks either page. */
  async function loadData() {
    const data = await (await fetch("data.json", { cache: "no-cache" })).json();
    const M = data.meta, ix = Object.fromEntries(M.columns.map((c, i) => [c, i]));
    const get = (r, c) => ix[c] != null ? r[ix[c]] : null;
    const sales = data.sales.map((r, id) => ({
      id, date: get(r, "date"), ym: get(r, "date").slice(0, 7), t: Date.parse(get(r, "date") + "T12:00"),
      nb: get(r, "nbhd"), price: get(r, "price"), sqft: get(r, "sqft"), yb: get(r, "year_built"), lot: get(r, "lot_sqft"),
      zone: get(r, "zone"), addr: get(r, "address"), rec: get(r, "recorded"), beds: get(r, "beds"), baths: get(r, "baths"),
      zip: get(r, "zip") || "", pid: get(r, "pid"), lat: get(r, "lat"), lon: get(r, "lon"),
    }));
    return { meta: M, cpi: data.cpi, sales, hasColumn: c => ix[c] != null };
  }

  /* One saved-settings object shared by both pages. Each page reads the keys it knows and
   * writes back merged, so neither page wipes the other's settings. */
  function loadState(defaults, meta) {
    const state = { ...defaults };
    try { const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "null"); if (saved) for (const k of Object.keys(state)) if (k in saved) state[k] = saved[k]; } catch (e) {}
    // Bed/bath data can come and go on Denver's side; reset size/homes filters when the mode changes.
    if (meta && state.mode !== meta.beds_mode) { state.minSqft = meta.default_min_sqft; state.homes = "32"; state.mode = meta.beds_mode; }
    return state;
  }
  function saveState(state) {
    try { const cur = JSON.parse(localStorage.getItem(STORE_KEY) || "{}"); localStorage.setItem(STORE_KEY, JSON.stringify({ ...cur, ...state })); } catch (e) {}
  }

  window.DNSD = { STORE_KEY, PRICE_CAP, el, css, dark, fmt$, fmtK, fmtPct, fmtD, slug, median, addMonths, zillow, loadData, loadState, saveState };
})();
