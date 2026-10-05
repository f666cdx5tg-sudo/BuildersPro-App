"""BuildersPro v3.56: the dock hides while scrolling and returns after you stop. Run: python3 test_v356.py"""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8803', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page()
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e) + ' ' + str(getattr(e, 'stack', ''))[:300]))
            await pg.goto('http://localhost:8803/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("(function(){var l=document.getElementById('bp-lock'); if(l) l.remove();})()")
            await pg.evaluate("showScreen('s-jobs')"); await pg.wait_for_timeout(300)
            # make the page tall enough to scroll
            await pg.evaluate("(function(){var d=document.createElement('div');d.id='tall';d.style.cssText='height:3000px';document.querySelector('.screen.active').appendChild(d)})()")
            away = lambda: pg.evaluate("document.getElementById('bp-dock').classList.contains('bp-dock-away')")
            ok(not await away(), 'dock should start visible')
            await pg.mouse.move(200, 400); await pg.mouse.wheel(0, 500); await pg.wait_for_timeout(250)
            ok(await away(), 'dock should hide while scrolling')
            op = await pg.evaluate("getComputedStyle(document.getElementById('bp-dock')).opacity")
            ok(float(op) < 0.5, f'dock should be faded out, opacity {op}')
            await pg.wait_for_timeout(1100)
            ok(not await away(), 'dock should come back after scrolling stops')
            await pg.mouse.wheel(0, 300); await pg.wait_for_timeout(200); ok(await away(), 'hides again on a second scroll')
            await pg.touchscreen.tap(200, 300) if False else await pg.evaluate("(function(){var ev=new Event('touchstart',{bubbles:true});ev.touches=[{clientX:5,clientY:5}];document.body.dispatchEvent(ev)})()"); await pg.wait_for_timeout(100)
            ok(not await away(), 'a touch brings it back at once')
            ok(len(errs) == 0, f'console errors {errs[:3]}')
            await b.close()
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
