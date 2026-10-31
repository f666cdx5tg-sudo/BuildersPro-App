"""v6.7.4 — the iPad app opens the Command Center; switch to the field app and back; iPhone and browsers unchanged.
Run from repo root: python3 test_v674_ipad_cc.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8974
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SHELL = "window.BPShell = { version: 't', caps: { ai: true } }; window.webkit = { messageHandlers: { bp: { postMessage: function(){} } } };"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/604.1 BuildersProShell'
async def open_(b, ua, touch, shell, w, h, path='index.html'):
    ctx = await b.new_context(viewport={'width': w, 'height': h}, user_agent=ua, has_touch=touch, is_mobile=False)
    if shell: await ctx.add_init_script(SHELL)
    if touch: await ctx.add_init_script("Object.defineProperty(navigator, 'maxTouchPoints', { get: function(){ return 5; } });")
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, path)); await pg.wait_for_timeout(3500)
    return ctx, pg, errs
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\niPad app')
            ctx, pg, errs = await open_(b, IPAD, True, True, 1366, 1024)
            ok(pg.url.endswith('desktop.html'), 'opens the Command Center (%s)' % pg.url)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            ok(await pg.evaluate("!!document.getElementById('ni-fieldapp')"), 'sidebar has "Field app"')
            pt = await pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.topbar')).paddingTop)")
            ok(pt >= 30, 'top bar sits below the iPad clock/battery row (padding %s px)' % pt)
            await pg.evaluate("document.getElementById('ni-fieldapp').click()"); await pg.wait_for_timeout(3500)
            ok(pg.url.endswith('index.html'), 'Field app switches to the field app (%s)' % pg.url)
            await pg.reload(); await pg.wait_for_timeout(3000)
            ok(pg.url.endswith('index.html'), 'and the iPad remembers it')
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            ok(await pg.evaluate("!!document.getElementById('nav-cc')"), 'side menu has "Command Center"')
            await pg.evaluate("document.getElementById('nav-cc').click()"); await pg.wait_for_timeout(3500)
            ok(pg.url.endswith('desktop.html'), 'Command Center switches back')
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            print('\niPhone app')
            ctx, pg, errs = await open_(b, IPHONE, True, True, 402, 874)
            ok(pg.url.endswith('index.html') and not await pg.evaluate("!!document.getElementById('nav-cc')"), 'iPhone stays on the field app, no switch button')
            await ctx.close()
            print('\nBrowser')
            ctx, pg, errs = await open_(b, IPAD, True, False, 1366, 1024)
            ok(pg.url.endswith('index.html'), 'a browser (not the app) is not redirected')
            await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
