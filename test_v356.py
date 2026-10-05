"""BuildersPro v3.57: the dock is hidden until you scroll/tap/change screen, shows ~3 s, then hides. Run: python3 test_v356.py"""
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
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('http://localhost:8803/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("(function(){var l=document.getElementById('bp-lock'); if(l) l.remove();})()")
            await pg.wait_for_timeout(4200)   # let the start-up reveal finish
            on = lambda: pg.evaluate("document.getElementById('bp-dock').classList.contains('bp-dock-on')")
            op = lambda: pg.evaluate("parseFloat(getComputedStyle(document.getElementById('bp-dock')).opacity)")
            ok(not await on(), 'dock should be hidden at rest')
            await pg.wait_for_timeout(300); ok(await op() < 0.1, 'hidden dock should be fully faded')
            await pg.evaluate("showScreen('s-jobs')"); await pg.wait_for_timeout(300)
            ok(await on(), 'changing screen should show the dock briefly')
            await pg.wait_for_timeout(3600); ok(not await on(), 'dock should hide again after ~3 s')
            await pg.evaluate("(function(){var d=document.createElement('div');d.style.cssText='height:3000px';document.querySelector('.screen.active').appendChild(d)})()")
            await pg.mouse.move(200, 400); await pg.mouse.wheel(0, 500); await pg.wait_for_timeout(350)
            ok(await on(), 'scrolling should show the dock'); await pg.wait_for_timeout(300); ok(await op() > 0.8, 'dock should be visible while scrolling')
            await pg.wait_for_timeout(1500); ok(await on(), 'dock should still be there ~2 s later')
            await pg.wait_for_timeout(2400); ok(not await on(), 'dock should hide ~3 s after scrolling')
            await pg.evaluate("(function(){var ev=new Event('touchstart',{bubbles:true});ev.touches=[{clientX:5,clientY:5}];document.body.dispatchEvent(ev)})()"); await pg.wait_for_timeout(250)
            ok(await on(), 'a touch should show the dock')
            ok(len(errs) == 0, f'console errors {errs[:3]}')
            await b.close()
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
