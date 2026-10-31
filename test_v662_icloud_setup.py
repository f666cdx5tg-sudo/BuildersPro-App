"""v6.6.2 — iCloud sync survives a second copy of Apple's CloudKit script (the CONFIGURATION_ERROR on Stan's phone).
A fake CloudKit throws CONFIGURATION_ERROR unless configure() was called on THAT copy. Then the copy is swapped
for a fresh one (what a second script tag did). Sync must set up the new copy and get through.
Also: two syncs started at the same moment add the script only once.
Run from repo root: python3 test_v662_icloud_setup.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8962
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
FAKE = """
window.__ckLoads = (window.__ckLoads || 0) + 1;
window.CloudKit = (function(){
  var configured = false;
  function err(){ var e = new Error('CONFIGURATION_ERROR: Please configure CloudKit'); e.ckErrorCode = 'CONFIGURATION_ERROR'; return e; }
  var db = { fetchRecords: function(){ return Promise.resolve({ records: [] }); }, saveRecords: function(){ return Promise.resolve({ records: [] }); }, deleteRecords: function(){ return Promise.resolve({}); } };
  var c = { setUpAuth: function(){ return Promise.resolve({ userRecordName: 'u' }); }, whenUserSignsIn: function(){ return new Promise(function(){}); }, privateCloudDatabase: db };
  return { configure: function(){ configured = true; }, getDefaultContainer: function(){ if (!configured) throw err(); return c; } };
})();
"""
async def run(b, file, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    async def ck(route):
        await asyncio.sleep(0.3)
        await route.fulfill(status=200, content_type='application/javascript', body=FAKE)
    await pg.route('**/cloudkit.js', ck)
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.fallback())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); localStorage.setItem('bp_ck_on','1')")
    await pg.evaluate("delete window.CloudKit; window.__ckLoads = 0; [].forEach.call(document.querySelectorAll('script[src*=cloudkit]'), function(s){ s.remove(); })")
    await pg.evaluate("Promise.all([bpICloudSync('both'), new Promise(function(r){ setTimeout(function(){ r(bpICloudSync('pull')); }, 5); })])"); await pg.wait_for_timeout(1500)
    ok(await pg.evaluate("window.__ckLoads") == 1, 'two syncs at once load the iCloud script once (%s)' % await pg.evaluate("window.__ckLoads"))
    st = await pg.evaluate("__bpCk()")
    ok(not st['err'], 'first sync has no error (%s)' % st['err'])
    await pg.evaluate("""(function(){ var s = document.createElement('script'); s.textContent = %s; document.head.appendChild(s); })()""" % repr(FAKE))
    r = await pg.evaluate("bpICloudSync('both').then(function(x){ return [x, __bpCk().err]; })")
    ok(r[0] is not None and not r[1], 'after the script is swapped for a fresh copy, sync sets it up and works (%s)' % r)
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
