"""BuildersPro v4.53 (location + weather: fallbacks, cache, refresh, tap to retry).
Run from repo root: python3 test_v452.py. Exit 0 = all pass.
All network calls are mocked with Playwright routes."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
WX = {'current_weather': {'temperature': 61.4, 'weathercode': 2}}
WX_NEW = {'current': {'temperature_2m': 33.2, 'weather_code': 73}}
NOM = {'address': {'city': 'Bergenfield', 'state': 'New Jersey', 'ISO3166-2-lvl4': 'US-NJ', 'postcode': '07621'}}
BDC = {'city': 'Teaneck', 'principalSubdivisionCode': 'US-NJ', 'postcode': '07666'}
IPA = {'latitude': 40.89, 'longitude': -74.0, 'city': 'Hackensack', 'region_code': 'NJ', 'postal': '07601'}
IPW = {'success': True, 'latitude': 40.7, 'longitude': -74.0, 'city': 'Newark', 'region_code': 'NJ', 'postal': '07102'}
async def setup(b, mode, geo=True, cache=None, w=390, h=844):
    """mode: dict of host -> 'ok' | 'fail' | 'slow' | json"""
    ctx = await b.new_context(viewport={'width': w, 'height': h}, geolocation={'latitude': 40.9268, 'longitude': -73.9957} if geo else None, permissions=['geolocation'] if geo else [])
    pg = await ctx.new_page(); calls = {'wx': 0, 'nom': 0, 'bdc': 0, 'ipa': 0, 'ipw': 0}
    async def handler(route):
        u = route.request.url
        for key, host, data in (('wx','open-meteo.com',WX),('nom','nominatim',NOM),('bdc','bigdatacloud',BDC),('ipa','ipapi.co',IPA),('ipw','ipwho.is',IPW)):
            if host in u:
                calls[key] += 1
                m = mode.get(key, 'ok')
                if callable(m): m = m(calls[key])
                if m == 'fail': await route.abort(); return
                if m == 'rate': await route.fulfill(status=429, content_type='application/json', body='{"error":true}'); return
                if isinstance(m, dict): await route.fulfill(status=200, content_type='application/json', headers={'access-control-allow-origin':'*'}, body=json.dumps(m)); return
                await route.fulfill(status=200, content_type='application/json', headers={'access-control-allow-origin':'*'}, body=json.dumps(data)); return
        await route.continue_()
    await pg.route('**/*', handler)
    if cache is not None:
        await pg.add_init_script("try{localStorage.setItem('bp_geo_cache', %s)}catch(e){}" % json.dumps(json.dumps(cache)))
    return ctx, pg, calls
async def load(pg, wait=3200):
    await pg.goto('http://localhost:8786/index.html'); await pg.wait_for_timeout(wait)
    await pg.evaluate("document.getElementById('bp-lock')?.remove()")
async def read(pg):
    return await pg.evaluate("({loc:document.getElementById('info-loc-text').textContent,wx:document.getElementById('info-weather-text').textContent,ico:document.getElementById('info-weather-icon').textContent,geo:window._currentGeo||'',cw:window._currentWeather||''})")
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8786','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
      async with async_playwright() as p:
        b = await p.chromium.launch()
        # 1 everything works
        ctx, pg, calls = await setup(b, {}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await load(pg); r = await read(pg)
        ok(await pg.evaluate("APP_VERSION==='4.53'"), 'version')
        ok(r['loc'] == 'Bergenfield NJ 07621' and r['geo'] == 'Bergenfield NJ 07621', f'1 place {r}')
        ok(r['wx'] == '61°F Partly Cloudy' and r['cw'] == '⛅ 61°F Partly Cloudy', f'1 weather {r}')
        ok(len(errs) == 0, f'1 errors {errs}'); await ctx.close()
        # 2 new-style weather response + snow icon
        ctx, pg, calls = await setup(b, {'wx': WX_NEW}); await load(pg); r = await read(pg)
        ok(r['wx'] == '33°F Snow' and r['ico'] == '🌨', f'2 new weather format {r}'); await ctx.close()
        # 3 nominatim down -> bigdatacloud
        ctx, pg, calls = await setup(b, {'nom': 'fail'}); await load(pg, 4200); r = await read(pg)
        ok(r['geo'] == 'Teaneck NJ 07666', f'3 reverse fallback {r}'); await ctx.close()
        # 4 every reverse lookup down -> coordinates still stamped (never empty)
        ctx, pg, calls = await setup(b, {'nom': 'fail', 'bdc': 'fail'}); await load(pg, 4500); r = await read(pg)
        ok(r['geo'] == '40.9268, -73.9957' and r['loc'] == '40.9268, -73.9957', f'4 coords stamped {r}')
        ok(r['wx'] == '61°F Partly Cloudy', f'4 weather still works {r}'); await ctx.close()
        # 5 GPS denied, ipapi rate-limited -> ipwho.is
        ctx, pg, calls = await setup(b, {'ipa': 'rate'}, geo=False); await load(pg, 4200); r = await read(pg)
        ok(r['geo'] == 'Newark NJ 07102' and r['wx'].startswith('61'), f'5 IP fallback chain {r}'); await ctx.close()
        # 6 GPS denied + both IP services down + saved copy -> last known (the old code showed nothing)
        saved = {'place': 'Fair Lawn NJ 07410', 'lat': '40.94', 'lng': '-74.12', 'wx': {'ico': '☀️', 'txt': 'Clear', 'temp': 70, 'at': int(time.time()*1000) - 3600*1000}}
        ctx, pg, calls = await setup(b, {'ipa': 'fail', 'ipw': 'fail', 'wx': 'fail'}, geo=False, cache=saved); await load(pg, 5000); r = await read(pg)
        ok(r['geo'] == 'Fair Lawn NJ 07410' and r['loc'] == 'Fair Lawn NJ 07410', f'6 last known place {r}')
        ok(r['wx'] == '70°F Clear', f'6 last known weather (1h old) {r}'); await ctx.close()
        # 7 stale weather (>3h) is not shown as current
        saved['wx']['at'] = int(time.time()*1000) - 5*3600*1000
        ctx, pg, calls = await setup(b, {'ipa': 'fail', 'ipw': 'fail', 'wx': 'fail'}, geo=False, cache=saved); await load(pg, 5000); r = await read(pg)
        ok(r['wx'] == 'Tap to retry' and r['cw'] == '', f'7 stale weather hidden {r}'); await ctx.close()
        # 8 nothing works, nothing saved -> "Tap to retry", never stuck on Detecting.../N/A; tap retries and recovers
        flag = {'down': True}
        ctx, pg, calls = await setup(b, {'ipa': lambda n: 'fail' if flag['down'] else IPA, 'ipw': lambda n: 'fail' if flag['down'] else IPW, 'wx': lambda n: 'fail' if flag['down'] else WX, 'nom': lambda n: 'fail' if flag['down'] else NOM}, geo=False)
        await load(pg, 6500); r = await read(pg)
        ok(r['loc'] == 'Tap to retry' and r['wx'] == 'Tap to retry', f'8 shows retry prompt {r}')
        flag['down'] = False
        await pg.evaluate("document.getElementById('info-loc-text').click()"); await pg.wait_for_timeout(2500); r = await read(pg)
        ok(r['geo'] == 'Hackensack NJ 07601' and r['wx'] == '61°F Partly Cloudy', f'8 tap recovers {r}'); await ctx.close()
        # 9 weather: first call fails, automatic retry succeeds
        ctx, pg, calls = await setup(b, {'wx': lambda n: 'fail' if n == 1 else WX}); await load(pg, 3800); r = await read(pg)
        ok(r['wx'] == '61°F Partly Cloudy' and calls['wx'] == 2, f'9 weather retry {r} {calls}'); await ctx.close()
        # 10 hung weather server does not hang the app (times out, shows retry)
        ctx, pg, calls = await setup(b, {'wx': 'slow'}); 
        async def slow(route): await asyncio.sleep(60)
        await pg.route('**/api.open-meteo.com/**', slow); await load(pg, 19000); r = await read(pg)
        ok(r['wx'] == 'Tap to retry' and r['geo'] == 'Bergenfield NJ 07621', f'10 hung weather server times out, place still shown {r}')
        await ctx.close()
        # 11 coming back to the app refreshes (after the throttle window) and reflects a new place
        place = {'v': NOM}
        ctx, pg, calls = await setup(b, {'nom': lambda n: place['v']}); await load(pg)
        place['v'] = {'address': {'city': 'Paterson', 'state': 'New Jersey', 'ISO3166-2-lvl4': 'US-NJ', 'postcode': '07501'}}
        await pg.evaluate("window.bpGeoRefresh()"); await pg.wait_for_timeout(2500); r = await read(pg)
        ok(r['geo'] == 'Paterson NJ 07501', f'11 manual refresh {r}')
        n = calls['wx']; await pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(800)
        ok(calls['wx'] == n, f'11 returning to the app inside 5 min does not hammer the APIs {calls}')
        await pg.evaluate("window.dispatchEvent(new Event('online'))"); await pg.wait_for_timeout(2500)
        ok(calls['wx'] > n, f'11 coming back online refreshes {calls}')
        # saved copy written for next launch
        c = await pg.evaluate("JSON.parse(localStorage.getItem('bp_geo_cache'))")
        ok(c.get('place') and c.get('wx') and c['wx']['temp'] == 61, f'11 cache saved {c}'); await ctx.close()
        # 12 photo / receipt stamps read the same globals
        ctx, pg, calls = await setup(b, {}); await load(pg)
        ok(await pg.evaluate("window._currentGeo==='Bergenfield NJ 07621' && window._currentWeather.indexOf('61°F')>-1"), '12 stamps get location + weather')
        await ctx.close()
        await b.close()
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
