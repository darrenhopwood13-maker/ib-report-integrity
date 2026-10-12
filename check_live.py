#!/usr/bin/env python3
"""Look at the published page in a real browser, phone and desktop."""
from playwright.sync_api import sync_playwright

URL = "https://darrenhopwood13-maker.github.io/ib-report-integrity/"
CHROME = "/root/.hermes/profiles/banksy/home/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"
OUT = "/root/.hermes/profiles/banksy/outputs/ib-report-integrity"

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME,
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--headless=new"])
    for label, size in (("phone", {"width": 390, "height": 844}), ("desktop", {"width": 1280, "height": 900})):
        errs, failed = [], []
        ctx = b.new_context(viewport=size, device_scale_factor=2)
        pg = ctx.new_page()
        pg.on("console", lambda m: errs.append(m.text[:120]) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)[:120]))
        pg.on("requestfailed", lambda r: failed.append(r.url))
        pg.goto(URL, wait_until="load")
        pg.wait_for_timeout(5000)
        qr = pg.evaluate("() => { const i = document.querySelector('.foot img'); return i ? {src: (i.currentSrc || i.src).split('/').pop(), naturalWidth: i.naturalWidth} : null; }")
        fonts = pg.evaluate("() => document.fonts.status")
        head = pg.evaluate("() => document.querySelector('h1').textContent")
        accent = pg.evaluate("() => getComputedStyle(document.querySelector('.wordmark i')).color")
        h = pg.evaluate("() => document.body.scrollHeight")
        print(f"{label}: h1 present={bool(head)} | fonts={fonts} | accent={accent} | QR={qr} | height={h}px")
        pg.screenshot(path=f"{OUT}/live-{label}.png", full_page=True)
        print(f"   console errors: {len(errs)} {errs[:2]} | failed requests: {len(failed)} {failed[:2]}")
        ctx.close()
    b.close()
