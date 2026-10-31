"""v6.6.1 — work saved on a removed job copy comes back; save chip shows saved / iCloud state.
Simulates: Find duplicates removed copy j2 of N. Peach St (job + its Kitchen room in the Recycle Bin);
the phone was still On Site at j2 and added a punch item, a daily log and a photo to it.
Run from repo root: python3 test_v661_rescue_save.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8961
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString(), d = t.slice(0,10);
  DB.jobs=[{id:'j1',name:'N. Peach St',address:'1536 N. Peach St',status:'Active'},{id:'j3',name:'Other',address:'2 St',status:'Active'}];
  DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1'}];
  DB.recycle=[{id:'rc_jobs_j2',coll:'jobs',rec:{id:'j2',name:'N. Peach St',address:'1536 N. Peach St'},deletedAt:t},
              {id:'rc_rooms_r2',coll:'rooms',rec:{id:'r2',jobId:'j2',name:'Kitchen',level:'Level 1'},deletedAt:t}];
  DB.punchlist=[{id:'k1',jobId:'j1',roomId:'r1',text:'Old item',done:false},{id:'k9',jobId:'j2',roomId:'r2',text:'Added today on the phone',done:false,created:t}];
  DB.reports=[{id:'rp9',jobId:'j2',date:d,notes:'Today log'}];
  DB.photos=[{id:'ph9',jobId:'j2',roomId:'r2',src:'data:image/png;base64,AA',date:t}];
  DB.expenses=[{id:'e9',jobId:'jX',amount:5,desc:'orphan from a job deleted long ago, no match'}];
  try{bpSave()}catch(e){try{saveDB()}catch(e2){}} }"""
async def run(b, file, w, h, mobile):
    ctx = await b.new_context(viewport={'width':w,'height':h}, is_mobile=mobile, has_touch=mobile)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()"); await pg.evaluate(SEED)
    n = await pg.evaluate("bpRescueOrphans()")
    r = await pg.evaluate("({k:DB.punchlist.find(function(x){return x.id==='k9'}), rp:DB.reports[0].jobId, ph:DB.photos[0], e:DB.expenses[0].jobId})")
    ok(n == 3, 'brought back 3 records (%s)' % n)
    ok(r['k']['jobId'] == 'j1' and r['k']['roomId'] == 'r1', 'punch item moved to the kept job and its Kitchen')
    ok(r['rp'] == 'j1' and r['ph']['jobId'] == 'j1' and r['ph']['roomId'] == 'r1', 'daily log and photo moved too')
    ok(r['e'] == 'jX', 'an orphan with no matching job is left alone')
    ok(await pg.evaluate("bpRescueOrphans()") == 0, 'running again changes nothing')
    if mobile:
        await pg.evaluate("showScreen('s-home')")
    await pg.wait_for_timeout(1800)
    await pg.evaluate("bpSaveChipPaint()")
    txt = await pg.evaluate("(document.getElementById('bp-save-chip')||{}).textContent || ''")
    ok('Saved' in txt or 'iCloud' in txt, 'save chip shows (%s)' % txt)
    await pg.evaluate("localStorage.removeItem('bp_ck_on'); bpSaveChipPaint()")
    ok('OFF' in await pg.evaluate("(document.getElementById('bp-save-chip').title || document.getElementById('bp-save-chip').textContent)"), 'iCloud off is shown in red with tap to turn on')
    await pg.evaluate("localStorage.setItem('bp_ck_on','1'); bpSaveChipPaint()")
    tx = (await pg.evaluate("(document.getElementById('bp-save-chip').title || document.getElementById('bp-save-chip').textContent)")).lower()
    ok('sign in' in tx or 'not synced' in tx, 'iCloud on but not signed in says so (%s)' % tx)
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\niPhone'); await run(b, 'index.html', 402, 874, True)
            print('\nMac'); await run(b, 'desktop.html', 1440, 900, False)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
