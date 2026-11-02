"""v6.9.9 — Home: with a job On Site, the bottom shows that job's notes & comments instead of Recent Jobs.
Run from repo root: python3 test_v699_home_notes.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 9001
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={'width':402,'height':874}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            await pg.evaluate("""() => { DB.jobs=[{id:'jP',name:'N. Peach St',status:'Active'},{id:'jS',name:'Shedwick',status:'Active'}];
              DB.rooms=[{id:'r1',jobId:'jP',name:'Kitchen'}];
              DB.jobNotes=[{id:'n1',jobId:'jP',roomId:'r1',text:'Client wants matte black faucet',created:'2026-10-30T10:00:00Z'},{id:'n2',jobId:'jS',text:'SHEDWICK NOTE',created:'2026-10-31T10:00:00Z'}];
              DB.punchlist=[{id:'k1',jobId:'jP',roomId:'r1',text:'Set toilet',extraNotes:'Wax ring on order',done:false,updatedAt:'2026-10-31T09:00:00Z'},{id:'k2',jobId:'jP',text:'No note',extraNotes:'',done:false}];
              DB.reports=[{id:'d1',jobId:'jP',date:'2026-10-29',clientNotes:'Client visited, happy with tile'}];
              bpSave(); bpSetActiveJob('', true); showScreen('s-home'); }""")
            await pg.wait_for_timeout(500)
            ok(await pg.evaluate("!!document.getElementById('home-recent-jobs').offsetParent") and not await pg.evaluate("!!(document.getElementById('bp-home-notes')||{}).offsetParent"), 'no On Site job: Recent Jobs as before')
            await pg.evaluate("bpSetActiveJob('jP', true)"); await pg.wait_for_timeout(500)
            ok(not await pg.evaluate("!!document.getElementById('home-recent-jobs').offsetParent"), 'On Site: Recent Jobs is gone')
            t = await pg.evaluate("document.getElementById('bp-home-notes').innerText")
            ok('notes & comments' in t.lower() and '1 note · 2 comments' in t, 'Notes & comments with counts (%s)' % t.split(chr(10))[:3])
            ok('matte black faucet' in t and 'Wax ring on order' in t and 'happy with tile' in t and 'SHEDWICK' not in t, 'shows the job note, punch comment and daily-log note, nothing from Shedwick')
            order = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-home-notes div[onclick]'), function(e){ return e.lastElementChild.textContent.slice(0,12); })")
            ok(len(order) == 3 and 'Set toilet' in order[0], 'newest first (%s)' % order)
            ok('Kitchen' in t, 'shows the space')
            await pg.evaluate("bpSetActiveJob('jS', true)"); await pg.wait_for_timeout(500)
            t = await pg.evaluate("document.getElementById('bp-home-notes').innerText")
            ok('SHEDWICK NOTE' in t and 'faucet' not in t, 'switching On Site switches the notes')
            ok(not errs, 'no page errors %s' % errs[:2])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
