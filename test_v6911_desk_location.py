"""v6.9.11 — Command Center location: never the internet-address guess; Mac location → last place found
→ the place typed by clicking the location (default Bergenfield NJ 07621).
Run from repo root: python3 test_v6911_desk_location.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 9013
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def route(r):
    u = r.request.url
    if 'ipapi.co' in u: return await r.fulfill(status=200, content_type='application/json', body=json.dumps({'latitude': 40.92, 'longitude': -74.27, 'city': 'Wayne', 'region_code': 'NJ', 'postal': '07470'}))
    if 'nominatim' in u and '/reverse' in u: return await r.fulfill(status=200, content_type='application/json', body=json.dumps({'address': {'town': 'Bergenfield', 'state': 'New Jersey', 'postcode': '07621'}}))
    if 'nominatim' in u and '/search' in u: return await r.fulfill(status=200, content_type='application/json', body=json.dumps([{'lat': '40.75', 'lon': '-73.99'}]))
    if 'open-meteo' in u: return await r.fulfill(status=200, content_type='application/json', body=json.dumps({'current_weather': {'temperature': 60, 'weathercode': 0}}))
    if any(x in u for x in ('bigdatacloud','ipwho','api.github','apple-cloudkit','googleapis','gstatic')): return await r.abort()
    await r.continue_()
async def page(b, geo, init=''):
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, geolocation=geo, permissions=['geolocation'] if geo else [])
    if init: await ctx.add_init_script(init)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', route)
    await pg.goto('http://localhost:%d/desktop.html' % PORT)
    return ctx, pg, errs
LOC = "document.getElementById('tb-loc').textContent"
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\nMac location turned off, nothing saved')
            ctx, pg, errs = await page(b, None, "navigator.geolocation.getCurrentPosition=function(ok,bad){ setTimeout(function(){ bad({code:1}); }, 50); };")
            await pg.wait_for_timeout(2000)
            ok(await pg.evaluate(LOC) == 'Bergenfield NJ 07621', 'shows Bergenfield NJ 07621, not the internet guess "Wayne" (%s)' % await pg.evaluate(LOC))
            await ctx.close()
            print('\nMac location works')
            ctx, pg, errs = await page(b, {'latitude': 40.9276, 'longitude': -73.9974})
            await pg.wait_for_timeout(3000)
            ok('Bergenfield' in await pg.evaluate(LOC) and 'Wayne' not in await pg.evaluate(LOC), 'shows the Mac location: %s' % await pg.evaluate(LOC))
            saved = await pg.evaluate("localStorage.getItem('bp_desk_place')")
            ok(saved and 'Bergenfield' in saved, 'remembers it')
            print('\nClick the location and type one')
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            pg.once('dialog', lambda d: asyncio.ensure_future(d.accept('Manhattan NY 10001')))
            await pg.click('#tb-loc'); await pg.wait_for_timeout(800)
            ok(await pg.evaluate(LOC) == 'Manhattan NY 10001', 'typed place shows')
            await pg.reload(); await pg.wait_for_timeout(2500)
            ok(await pg.evaluate(LOC) == 'Manhattan NY 10001', 'and stays after reopening, even with the Mac location on')
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
