"""v6.6.4 — second copy, Save button, back where you left off.
1. Save button is in the bottom buttons + side menu (phone) and top bar (Mac); tapping it saves and says so.
2. The phone refuses every main save; the change is still in the second copy; reopening recovers it.
3. Leaving the app (page hidden) saves at once and remembers the screen; reopening within 2 h opens it
   (same job); older than 2 h → Home.
Run from repo root: python3 test_v664_save_resume.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8966
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { DB.jobs=[{id:'j1',name:'Job A',status:'Active'},{id:'j2',name:'Job B',status:'Active'}]; DB.punchlist=[]; bpSave(); }"""
HIDE = "Object.defineProperty(document, 'hidden', {configurable:true, get:function(){return true}}); document.dispatchEvent(new Event('visibilitychange')); Object.defineProperty(document, 'hidden', {configurable:true, get:function(){return false}});"
async def page(ctx, file):
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    toasts = []; pg.on('console', lambda m: None)
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2600)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.__toasts=[]; var t=window.toast; window.toast=function(m){ __toasts.push(m); return t && t.apply(this, arguments); }")
    return pg, errs
async def phone(b):
    ctx = await b.new_context(viewport={'width':402,'height':874}, is_mobile=True, has_touch=True)
    pg, errs = await page(ctx, 'index.html'); await pg.evaluate(SEED); await pg.wait_for_timeout(600)
    print('\n1. Save button')
    ok(await pg.evaluate("!!document.getElementById('bp-dock-save') && !!document.getElementById('nav-save')"), 'Save is in the bottom buttons and the side menu')
    r = await pg.evaluate("bpSaveNow('button')")
    ok(r['device'] and r['copy'], 'Save writes the main save and the second copy %s' % r)
    ok(any('Saved on this phone' in t for t in (await pg.evaluate("__toasts")) if t), 'and says "Saved on this phone" %s' % await pg.evaluate("__toasts"))
    print('\n2. Main save refused all the time')
    await pg.evaluate("""(function(){ var real = IDBDatabase.prototype.transaction;
      IDBDatabase.prototype.transaction = function(st, mode){ if (mode === 'readwrite') { var e = new Error('stopped'); e.name = 'UnknownError'; throw e; } return real.apply(this, arguments); }; })()""")
    await pg.evaluate("DB.punchlist.push({id:'k1',jobId:'j1',text:'Only in the second copy',done:false}); bpSave();"); await pg.wait_for_timeout(1500)
    r = await pg.evaluate("bpSaveNow('button')")
    ok(not r['device'] and r['copy'], 'main save fails, second copy holds it %s' % r)
    ok(any('backup copy WAS saved' in t for t in (await pg.evaluate("__toasts")) if t), 'tells you a backup copy was saved')
    await pg.close()
    pg, errs = await page(ctx, 'index.html'); await pg.wait_for_timeout(800)
    ok(await pg.evaluate("(DB.punchlist||[]).some(function(x){return x.id==='k1'})"), 'reopening the app brings the change back from the second copy')
    await pg.wait_for_timeout(800)
    ok(await pg.evaluate("!localStorage.getItem('bp_dirty_at')"), 'and the main save now holds it (nothing left unconfirmed)')
    print('\n3. Leave and come back')
    await pg.evaluate("openJobDetail('j2')"); await pg.wait_for_timeout(500)
    await pg.evaluate(HIDE); await pg.wait_for_timeout(800)
    ok(await pg.evaluate("JSON.parse(localStorage.getItem('bp_resume_v1')).job") == 'j2', 'leaving remembers the job page you were on')
    await pg.close()
    pg, errs = await page(ctx, 'index.html'); await pg.wait_for_timeout(800)
    ok(await pg.evaluate("document.querySelector('.screen.active').id") == 's-job-detail' and await pg.evaluate("currentJobId") == 'j2', 'reopening opens Job B again (%s)' % await pg.evaluate("document.querySelector('.screen.active').id"))
    await pg.close()
    await ctx.add_init_script("try { if (!sessionStorage.getItem('aged')) { sessionStorage.setItem('aged','1'); var r=JSON.parse(localStorage.getItem('bp_resume_v1')); r.at -= 3*3600*1000; localStorage.setItem('bp_resume_v1', JSON.stringify(r)); } } catch(e){}")
    pg, errs = await page(ctx, 'index.html'); await pg.wait_for_timeout(800)
    ok(await pg.evaluate("document.querySelector('.screen.active').id") == 's-job-detail', 'v6.7.9: even 3+ hours later it opens where you left off')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def mac(b):
    ctx = await b.new_context(viewport={'width':1440,'height':900})
    pg, errs = await page(ctx, 'desktop.html'); await pg.evaluate(SEED)
    print('\nMac')
    ok(await pg.evaluate("!!document.getElementById('tb-save')"), 'Save button in the top bar')
    r = await pg.evaluate("bpSaveNow('button')")
    ok(r['device'] and r['copy'], 'Save works on the Mac %s' % r)
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await phone(b); await mac(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
