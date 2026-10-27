"""BuildersPro v4.39 (light mode: bottom-right ••• button has black dots; dark mode keeps white).
Run from repo root: python3 test_v439.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
DOT = "getComputedStyle(document.querySelector('#bp-dock-menu svg.bp-dots circle')).fill"
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8795/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.53'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!!document.getElementById('bp-dock-menu')"), f'{t}: dock menu button exists')
        await pg.evaluate("document.documentElement.setAttribute('data-theme','light')"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate(DOT)=='rgb(0, 0, 0)', f'{t}: light-mode dots not black: {await pg.evaluate(DOT)}')
        await pg.screenshot(path=os.environ.get('SHOT_DIR','/tmp') + f'/dock_light_{w}.png', clip={'x':0,'y':h-220,'width':w,'height':220})
        await pg.evaluate("document.documentElement.setAttribute('data-theme','dark')"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate(DOT)=='rgb(255, 255, 255)', f'{t}: dark-mode dots should stay white: {await pg.evaluate(DOT)}')
        await pg.screenshot(path=os.environ.get('SHOT_DIR','/tmp') + f'/dock_dark_{w}.png', clip={'x':0,'y':h-220,'width':w,'height':220})
        # other ••• buttons untouched: still white on their dark circles in light mode
        await pg.evaluate("document.documentElement.setAttribute('data-theme','light')"); await pg.wait_for_timeout(200)
        other = await pg.evaluate("(()=>{var c=document.querySelector('.bp-hm-btn svg.bp-dots circle');return c?getComputedStyle(c).fill:'none'})()")
        ok(other in ('rgb(255, 255, 255)','none'), f'{t}: other option buttons changed: {other}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8795','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
