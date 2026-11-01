"""v6.9.8 — with a job picked in ON SITE, Home shows nothing from the other jobs.
Run from repo root: python3 test_v698_home_only_active.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8999
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
VISJOBS = "[].filter.call(document.querySelectorAll('#home-recent-jobs [onclick*=\"openJobDetail(\"]'), function(c){ return c.offsetParent; }).map(function(c){ return c.getAttribute('onclick').match(/'([^']+)'/)[1]; }).sort()"
TC = "[].map.call(document.getElementById('tc-job-select').options, function(o){ return o.value; })"
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={'width':402,'height':874}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            await pg.evaluate("""() => { var t=new Date().toISOString(); DB.jobs=[{id:'jP',name:'N. Peach St',status:'Active',updatedAt:t},{id:'jS',name:'Shedwick',status:'Active',updatedAt:t}]; bpSave(); bpSetActiveJob('', true); showScreen('s-home'); }""")
            await pg.wait_for_timeout(500)
            ok(await pg.evaluate(VISJOBS) == ['jP','jS'] and sorted(await pg.evaluate(TC)) == ['jP','jS'], 'no On Site job: Home shows both jobs')
            await pg.evaluate("bpSetActiveJob('jP', true)"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate(VISJOBS) == ['jP'], 'On Site = N. Peach St: Recent jobs shows only N. Peach St')
            ok(await pg.evaluate(TC) == ['jP'], 'Time Clock offers only N. Peach St')
            await pg.evaluate("showScreen('s-finance')"); await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate(VISJOBS) == ['jP'] and await pg.evaluate(TC) == ['jP'], 'still only N. Peach St after leaving Home and coming back')
            sel = await pg.evaluate("[].map.call(document.querySelector('.bp-activejob-wrap select').options, function(o){ return o.value; }).filter(Boolean).sort()")
            ok(sel == ['jP','jS'], 'the ON SITE picker still lists every job, to switch')
            await pg.evaluate("bpSetActiveJob('jS', true)"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate(VISJOBS) == ['jS'] and await pg.evaluate(TC) == ['jS'], 'switch to Shedwick: only Shedwick')
            await pg.evaluate("bpSetActiveJob('', true)"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate(VISJOBS) == ['jP','jS'] and sorted(await pg.evaluate(TC)) == ['jP','jS'], 'No active job: both back')
            ok(not errs, 'no page errors %s' % errs[:2])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
