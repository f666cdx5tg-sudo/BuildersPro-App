"""v6.9.17 — Outdoor space icons (Stan's picks, Nov 9 2026): no crane anywhere, ever.
Exterior spaces with any name (Rear of Building, Side of House) = house + tree; Gutters / Downspout =
Option C gutter (roof edge, gutter, spout, drop); Yard / Grading / Lawn / Garden / Backyard = Option C tree + fence;
Back Door / Rear Entrance = Option C door.
Checks the field app (iPhone) and Command Center (Mac), every icon lookup, and scans every screen for the crane.
Run from repo root: python3 test_v6917_outdoor_icons.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8917
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
HOUSE_TREE = 'M3 20.5v-8l5.5-4.5'; DOWNSPOUT = 'M3.5 9.5L21 3.5'; TREE = 'M12.6 15a3.1 3.1'; DOOR = 'M6.5 20V3.5h11V20'; CRANE = 'M11 9l8-4.5'
SPACES = [('Rear of Building','Exterior',HOUSE_TREE), ('Side of House','Exterior',HOUSE_TREE), ('Back Wall','Other',None),
          ('Gutters','Exterior',DOWNSPOUT), ('Downspouts','Exterior',DOWNSPOUT), ('Yard / Grading – Outside','Exterior',TREE),
          ('Front Lawn','Exterior',TREE), ('Garden','Exterior',TREE), ('Landscaping','Other',TREE), ('Backyard','Exterior',TREE), ('Back Door','Exterior',DOOR), ('Rear Entrance','Exterior',DOOR)]
SEED = """(sp) => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'Shedwick', client:'A', address:'1 St', status:'Active', updatedAt:t }];
 DB.rooms = sp.map(function(s, i){ return { id:'r'+i, jobId:'j1', name:s[0], type:s[1], space:'Exterior', updatedAt:t }; });
 DB.punchlist = [];
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, **kw):
    print('\n' + name)
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 17), name + ': on v6.9.17 or newer')
    await pg.evaluate(SEED, [list(s) for s in SPACES]); await pg.wait_for_timeout(300)
    ok(CRANE not in await pg.evaluate("window.bpIcon ? window.bpIcon('outside') + (window.bpIcon('crane')||'') : ''"), name + ': crane drawing no longer exists in the icon set')
    ok(HOUSE_TREE in await pg.evaluate("window.bpIcon('outside')"), name + ': 🏗 now means house + tree')
    for sp, ty, want in SPACES:
        h = await pg.evaluate("(function(n,t){ var a = window.bpRoomIconHtml ? window.bpRoomIconHtml(n,t) : ''; var b = (window.BPX && BPX.icon) ? BPX.icon({ name:n, type:t, space:'Exterior' }) : ''; return String(a) + '||' + String(b); })('%s','%s')" % (sp.replace("'", "\\'"), ty))
        ok(CRANE not in h and '🏗' not in h, '%s: "%s" — no crane' % (name, sp))
        if want: ok(want in h.split('||')[0], '%s: "%s" — %s' % (name, sp, {HOUSE_TREE:'house + tree', DOWNSPOUT:'gutter (C)', TREE:'tree + fence (C)', DOOR:'back door (C)'}[want]))
    # every screen: the job's spaces, home, jobs, search — scan the page for the crane
    pages = ["openJobDetail('j1')", "showScreen('s-home')", "showScreen('s-jobs')"] if 'index' in url else ["openJob && openJob('j1')", "showView('jobs')", "showView('dashboard')", "showView('rooms')"]
    if 'index' in url: pages.insert(1, "openRoomDetail('r0')")
    else: pages.insert(1, "openRoomDetail('r0')")
    for js in pages:
        try: await pg.evaluate(js); await pg.wait_for_timeout(700)
        except Exception as e: pass
        html = await pg.evaluate("document.body.innerHTML")
        ok(CRANE not in html and '🏗' not in await pg.evaluate("document.body.innerText"), '%s: no crane on screen after %s' % (name, js))
        if js.startswith("openJobDetail") or js.startswith("openJob "): await pg.screenshot(path='/tmp/claude-0/s/icons-%s.png' % name.split()[0])
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'Mac Command Center', 'desktop.html', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
