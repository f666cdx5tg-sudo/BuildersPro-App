"""BuildersPro v3.55: the thumb dock's Back button works on the main screens (goes to the last screen, else Home). Run: python3 test_v355.py"""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8801', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page()
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('http://localhost:8801/index.html'); await pg.wait_for_timeout(2500)
            scr = lambda: pg.evaluate("document.querySelector('.screen.active').id")
            hid = lambda: pg.evaluate("document.getElementById('bp-dock-back').hidden")
            go = lambda s: pg.evaluate(f"showScreen('{s}')")
            await pg.evaluate("(function(){var l=document.getElementById('bp-lock'); if(l) l.remove();})()")
            ok(await pg.evaluate("APP_VERSION==='3.57'"), 'version not 3.57')
            await go('s-home'); await pg.wait_for_timeout(300)
            ok(await scr() == 's-home' and await hid(), 'Back should be hidden on Home')
            await go('s-jobs'); await pg.wait_for_timeout(300)
            ok(not await hid(), 'Back should show on Jobs')
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350); await pg.click('#bp-dock-back'); await pg.wait_for_timeout(400)
            ok(await scr() == 's-home', 'Back from Jobs should return to Home')
            await go('s-jobs'); await go('s-punch'); await go('s-photos'); await pg.wait_for_timeout(300)
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350); await pg.click('#bp-dock-back'); await pg.wait_for_timeout(400)
            ok(await scr() == 's-punch', f'Back from Photos should return to Punch, got {await scr()}')
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350); await pg.click('#bp-dock-back'); await pg.wait_for_timeout(400)
            ok(await scr() == 's-jobs', f'Back from Punch should return to Jobs, got {await scr()}')
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350); await pg.click('#bp-dock-back'); await pg.wait_for_timeout(400)
            ok(await scr() == 's-home', 'Back from Jobs should end at Home')
            ok(await hid(), 'Back hidden again on Home')
            await go('s-finance'); await pg.wait_for_timeout(300)
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350); await pg.click('#bp-dock-back'); await pg.wait_for_timeout(400)
            ok(await scr() == 's-home', 'Back from Finance (opened from Home) should go Home')
            # jobs -> job detail -> back button still returns to Jobs (existing behaviour)
            await go('s-jobs'); await pg.wait_for_timeout(300)
            await pg.evaluate('bpDockShow()'); await pg.wait_for_timeout(350)
            box = await pg.evaluate("(()=>{const r=document.getElementById('bp-dock-back').getBoundingClientRect();const a=document.getElementById('bp-dock-add').getBoundingClientRect();return [r.right<=a.left+1, r.width>=40]})()")
            ok(box[0] and box[1], f'Back should sit left of + and be thumb-sized {box}')
            ok(len(errs) == 0, f'console errors {errs[:3]}')
            await pg.screenshot(path='/tmp/claude-0/v355-jobs.png')
            await b.close()
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
