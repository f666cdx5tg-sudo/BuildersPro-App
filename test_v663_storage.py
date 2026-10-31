"""v6.6.3 — saves survive the phone closing the app's storage connection.
1. Close the storage connection (what iOS does in the background), then make a change: it saves and reads back.
2. The phone refuses the first two writes: the save retries on a fresh connection and lands.
3. After a reload the change is still there.
Run from repo root: python3 test_v663_storage.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8964
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, file, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
    await pg.evaluate("DB.jobs = [{id:'j1',name:'Job A',status:'Active'}]; DB.punchlist = []")
    ok(await pg.evaluate("bpPersistNow()"), 'normal save works')
    # 1. iOS closes the connection
    await pg.evaluate("new Promise(function(r){ idbOpen(function(db){ db.close(); r(); }); })")
    await pg.evaluate("DB.punchlist.push({id:'k1',jobId:'j1',text:'Added after the phone closed storage',done:false})")
    ok(await pg.evaluate("bpPersistNow()"), 'save after the connection was closed still works')
    # 2. the phone refuses two writes
    await pg.evaluate("""(function(){ var n = 0, real = IDBDatabase.prototype.transaction;
      IDBDatabase.prototype.transaction = function(s, mode){ if (mode === 'readwrite' && n < 2) { n++; var e = new Error('stopped'); e.name = 'UnknownError'; throw e; } return real.apply(this, arguments); }; })()""")
    await pg.evaluate("DB.punchlist.push({id:'k2',jobId:'j1',text:'Second item',done:false})")
    ok(await pg.evaluate("bpPersistNow()"), 'two refused writes: retried on a fresh connection and saved')
    ok(not await pg.evaluate("!!(document.getElementById('bp-save-banner')||document.querySelector('[id*=save][id*=banner]')) && /NOT saved/.test((document.getElementById('bp-save-banner')||{}).textContent||'')"), 'no red NOT saved banner')
    # 3. reload
    await pg.reload(); await pg.wait_for_timeout(2500)
    ids = await pg.evaluate("(DB.punchlist||[]).map(function(x){return x.id}).sort()")
    ok(ids == ['k1','k2'], 'after reopening, both items are there %s' % ids)
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\niPhone'); await run(b, 'index.html', 402, 874)
            print('\nMac'); await run(b, 'desktop.html', 1440, 900)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
