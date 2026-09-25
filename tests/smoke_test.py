"""Browser smoke test for the dashboard and map. Run before pushing any change to docs/.

    pip install playwright && playwright install chromium   # once
    python tests/smoke_test.py                              # serves docs/ locally and checks both pages

Exits non-zero on the first failure. Base-map tiles may be blocked where this runs; the map test only
checks our own layers, not the basemap.
"""
import asyncio
import functools
import http.server
import sys
import threading
from pathlib import Path

from playwright.async_api import async_playwright

DOCS = Path(__file__).resolve().parent.parent / "docs"
PORT = 8799
BASE = f"http://localhost:{PORT}"
GL_ARGS = ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"]


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(("localhost", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


async def main():
    srv = serve()
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=GL_ARGS)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append(f"{page.url}: {e}"))

        print("Dashboard")
        await page.goto(f"{BASE}/"); await page.wait_for_timeout(1500)
        check(await page.locator("#tiles .tile").count() == 4, "four headline tiles")
        check(await page.locator("#chart svg").count() == 1, "chart renders")
        rows = await page.locator("#nbTable .nblink").count()
        check(rows >= 13, f"neighborhood table lists {rows} neighborhoods")
        check(await page.locator("#recent a.addr").count() > 0, "recent sales have Zillow links")
        await page.click('#overview .viewseg [data-v="trend"]'); await page.wait_for_timeout(300)
        check(await page.locator("#chart path.line").count() >= 1, "trend view draws median lines")

        print("Neighborhood page")
        await page.locator("#nbTable .nblink").first.click(); await page.wait_for_timeout(800)
        check("#n=" in page.url, "clicking a name opens its page")
        check(await page.locator("#dTable tbody tr").count() > 0, "every-sale table has rows")
        before = await page.inner_text("#dTableHint")
        dual = await page.query_selector(".dual"); bb = await dual.bounding_box()
        await page.mouse.move(bb["x"] + bb["width"] - 6, bb["y"] + 10); await page.mouse.down()
        await page.mouse.move(bb["x"] + bb["width"] * 0.3, bb["y"] + 10, steps=6); await page.mouse.up()
        await page.wait_for_timeout(300)
        check(await page.inner_text("#dTableHint") != before, "price slider filters the sales list")
        await page.click("#priceReset")

        print("Map")
        m = await ctx.new_page()
        m.on("pageerror", lambda e: errors.append(f"{m.url}: {e}"))
        await m.goto(f"{BASE}/map.html"); await m.wait_for_timeout(5000)
        homes = await m.inner_text("#listTitle")
        check(homes and not homes.startswith("0 "), f"list shows homes ({homes})")
        check(await m.locator(".nblabel").count() >= 13, "neighborhood labels placed")
        check(await m.locator(".legend .row").count() >= 4, "legend drawn")
        await m.locator(".card").first.click(); await m.wait_for_timeout(2500)
        check(await m.locator(".maplibregl-popup").count() == 1, "card click opens a popup")
        check(await m.locator(".pin").count() > 0, "price pins appear when zoomed in")
        check(await m.locator(".maplibregl-popup a.z").count() == 1, "popup has a Zillow link")

        print("Phone width")
        ph = await browser.new_page(viewport={"width": 390, "height": 800})
        for path in ["/", "/map.html"]:
            await ph.goto(BASE + path); await ph.wait_for_timeout(1500)
            sw = await ph.evaluate("document.documentElement.scrollWidth")
            check(sw <= 392, f"{path} has no sideways scroll at 390px ({sw}px)")

        await browser.close()
    srv.shutdown()
    check(not errors, "no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    print("All checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
