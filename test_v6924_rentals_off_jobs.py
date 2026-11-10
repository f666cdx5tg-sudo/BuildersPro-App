"""v6.9.24 — rental properties stay out of the Jobs list (iPhone + Command Center) but remain in DB / Rentals.
Run from repo root: python3 test_v6924_rentals_off_jobs.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8924
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = DB.jobs.filter(function(j){ return j.id !== 'cj1' && j.id !== 'rp1'; });
 DB.jobs.push({ id:'cj1', name:'Kitchen Remodel Zeta', status:'Active', created:t });
 DB.jobs.push({ id:'rp1', name:'Peach Rental Omega', address:'12 Peach St', status:'Active', rental:true, created:t });
 DB.rooms.push({ id:'ru1', name:'Unit 2', jobId:'rp1', type:'Other', kind:'room', unit:true, created:t, tenant:{ name:'Anna Lee' }, rent:2100, dueDay:1, rentPays:[], inventory:[] }); }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, fn, box, **kw):
    print('\n' + name)
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(6000)
    ok(await pg.evaluate("APP_VERSION") == '6.9.24', name + ': on v6.9.24')
    await pg.evaluate(SEED); await pg.evaluate(fn + '()'); await pg.wait_for_timeout(300)
    t = await pg.evaluate("(document.getElementById('%s')||{}).innerText || ''" % box)
    ok('Kitchen Remodel Zeta' in t, name + ': construction job on the Jobs list')
    ok('Peach Rental Omega' not in t, name + ': rental property not on the Jobs list')
    ok(await pg.evaluate("DB.jobs.some(function(j){ return j.id === 'rp1'; })"), name + ': rental still in the data')
    await pg.evaluate("bpRentOpen()"); await pg.wait_for_timeout(200)
    ok('Peach Rental Omega' in await pg.inner_text('#bp-rent'), name + ': rental shows in Rentals')
    await pg.evaluate("bpRentClose()")
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', 'renderJobs', 'jobs-list', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'Mac Command Center', 'desktop.html', 'renderDesktopJobs', 'jobs-table-wrap', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
