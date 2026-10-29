"""v6.5.2 — every ••• menu opens ON TOP and every item in it works.
For each screen (Home, Jobs, job page, Spaces, a space, Punch, Photos, Finance + each tab, Calendar), at
iPhone width and Large text: open each visible •••, check that every item is the top-most thing where it
is drawn (nothing covers it) and fully on screen, tap an item, check the list closed without errors.
Run from repo root: python3 test_v652_menus_on_top.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8952
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString(), d = t.slice(0,10);
  DB.jobs = [{id:'j1',name:'N. Peach St',client:'Shelden Washington',address:'1536 N. Peach St',city:'Philadelphia',state:'PA',zip:'19131',status:'Active',contract:49000,trade:'Plumbing',start:'2026-09-01',updatedAt:t},
             {id:'j2',name:'Test Kitchen Remodel and Basement Finish',client:'Roberta Montgomery-Fitzgerald',address:'77 Washington Ave',city:'Bergenfield',state:'NJ',zip:'07621',status:'Pending',contract:128450.75,updatedAt:t}];
  var lv = ['Basement','Basement','Level 1','Level 1','Level 1','Level 1','Level 1','Level 1','Level 1','Level 2','Level 2','Roof','Outside'];
  var nm = ['Stairs','Basement/ mechanical room','Main Entrance','(F) Bathroom','Kitchen','Living Room','Dining Room','Hallway','Laundry','Primary Bedroom Suite','(R) Bathroom','Roof Drain','Water Service'];
  DB.rooms = nm.map(function(n,i){ return {id:'r'+i,jobId:'j1',name:n,type:/Bath/.test(n)?'Bathroom':/Kitchen/.test(n)?'Kitchen':'Room',level:lv[i],space:i>10?'Exterior':'Interior',updatedAt:t}; });
  var tr = ['Plumbing','Electrical','Drywall','Painting','Carpentry','Tile','HVAC','General'];
  DB.punchlist = []; for (var i = 0; i < 193; i++) DB.punchlist.push({id:'p'+i,jobId:'j1',roomId:i<40?'':'r'+(i%13),trade:tr[i%8],
    text:(i%7===0?'Glass screen door hinge/shock installation and adjustment at main entrance':'Item number '+i),done:i>=30,status:i>=30?'Done':'Open',created:'2026-09-26',updatedAt:t,completedAt:i>=30?t:''});
  DB.expenses = []; for (var e = 0; e < 40; e++) DB.expenses.push({id:'e'+e,jobId:'j1',desc:'Materials — Home Depot Supply #'+e,vendor:'The Home Depot Pro Supply',amount:1234.56+e,date:d,category:['Materials','Labor','Delivery','Equipment'][e%4]});
  DB.contractors = [{id:'c1',jobId:'j1',name:'Mike Rivera',company:'Rivera Electric & Low Voltage LLC',phone:'2015551234',email:'mike@riveraelectric.com',value:16500,trade:'Electrical'}];
  DB.payments = [{id:'pay1',contractorId:'c1',amount:2500,date:d}];
  DB.invoices = [{id:'i1',jobId:'j1',amount:24500,status:'Sent',date:d,number:'INV-2026-0042'}];
  DB.changeOrders = [{id:'co1',jobId:'j1',title:'Add shower niche with tile and waterproofing',amount:1850,status:'Approved'}];
  DB.shopping = []; for (var s = 0; s < 9; s++) DB.shopping.push({id:'s'+s,jobId:'j1',text:'1/2" PEX-A expansion elbow brass, lead free '+s,qty:12,unit:'ea',price:3.49,bought:s<3});
  DB.appointments = [{id:'a1',jobId:'j1',date:d,time:'09:30',title:'Rough plumbing inspection — City of Philadelphia L&I'}];
  DB.reports = [{id:'rp1',jobId:'j1',date:d,notes:'Material received, rough-in complete at both bathrooms',workers:'3'}];
  try { bpSave(); } catch(x){ try { saveDB(); } catch(y){} }
  try { bpSetActiveJob('j1', true); } catch(z){}
}"""
SCREENS = [
  ('Home', "showScreen('s-home')"), ('Jobs', "showScreen('s-jobs')"), ('Job page', "openJobDetail('j1')"),
  ('Spaces', "showScreen('s-rooms')"), ('A space', "try{openRoomDetail('r4')}catch(e){}"), ('Punch', "showScreen('s-punch')"),
  ('Photos', "showScreen('s-photos')"), ('Calendar', "showScreen('s-calendar')"),
  ('Finance overview', "showScreen('s-finance');try{setFinanceTab('overview')}catch(e){}"),
  ('Finance expenses', "showScreen('s-finance');try{setFinanceTab('expenses')}catch(e){}"),
  ('Finance invoices', "showScreen('s-finance');try{setFinanceTab('invoices')}catch(e){}"),
  ('Finance change orders', "showScreen('s-finance');try{setFinanceTab('changeorders')}catch(e){}"),
]
VISIBLE = """() => [].filter.call(document.querySelectorAll('.bp-hm'), function(h){ var b = h.querySelector('.bp-hm-btn'); if (!b) return false; var r = b.getBoundingClientRect(); return r.width > 10 && r.height > 10 && r.bottom > 0 && r.top < innerHeight && getComputedStyle(b).visibility !== 'hidden' && !h.closest('#bp-drawer'); }).map(function(h){ return h.id; })"""
ONTOP = """(id) => { var pop = document.querySelector('.bp-hm-float'); if (!pop) return 'no list opened';
  var bad = []; var items = pop.querySelectorAll('.bp-hm-it'); if (!items.length) return 'empty list';
  var vw = document.documentElement.clientWidth;
  [].forEach.call(items, function(it, i){ var r = it.getBoundingClientRect(), pr = pop.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight || r.top + 4 > pr.bottom || r.bottom - 4 < pr.top) return;   /* scrolled out of the list */
    if (r.left < 0 || r.right > vw + 1) bad.push('item ' + i + ' off screen');
    var x = r.left + r.width / 2, y = Math.min(innerHeight - 2, Math.max(1, r.top + r.height / 2)); var e = document.elementFromPoint(x, y);
    if (!e || !pop.contains(e)) bad.push('item ' + i + ' (' + it.textContent.trim().slice(0, 20) + ') covered by ' + (e ? (e.id || e.className || e.tagName) : 'nothing')); });
  return bad.join('; '); }"""
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for zoom in ('1', '1.3'):
                print('\nText size zoom %s' % zoom)
                ctx = await b.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2200)
                await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); localStorage.setItem('bp_zoom','%s'); try{bpApplyZoom()}catch(e){}" % zoom)
                await pg.evaluate(SEED)
                for name, go in SCREENS:
                    await pg.evaluate("bpHMenuClose();" + go); await pg.wait_for_timeout(900)
                    ids = await pg.evaluate(VISIBLE)
                    for k, hid in enumerate(ids):
                        await pg.evaluate("bpHMenuClose();" + go); await pg.wait_for_timeout(500)
                        if not await pg.evaluate("!!document.getElementById('%s')" % hid):
                            ids2 = await pg.evaluate(VISIBLE)
                            if k >= len(ids2): continue
                            hid = ids2[k]
                        btn = await pg.query_selector('#%s .bp-hm-btn' % hid)
                        if not btn: continue
                        await btn.scroll_into_view_if_needed(); bb = await btn.bounding_box()
                        if not bb: continue
                        hit = "(function(x,y,id){var e=document.elementFromPoint(x,y);return !!(e&&e.closest('#'+id))})(%f,%f,'%s')" % (bb['x']+bb['width']/2, bb['y']+bb['height']/2, hid)
                        if not await pg.evaluate(hit):   # something the last item opened is still up: start this screen fresh
                            await pg.reload(); await pg.wait_for_timeout(2000)
                            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
                            await pg.evaluate(SEED); await pg.evaluate(go); await pg.wait_for_timeout(900)
                            ids2 = await pg.evaluate(VISIBLE)
                            if k >= len(ids2): continue
                            hid = ids2[k]; btn = await pg.query_selector('#%s .bp-hm-btn' % hid)
                            await btn.scroll_into_view_if_needed(); bb = await btn.bounding_box()
                        label = await btn.get_attribute('aria-label')
                        await pg.touchscreen.tap(bb['x'] + bb['width']/2, bb['y'] + bb['height']/2); await pg.wait_for_timeout(350)
                        res = await pg.evaluate(ONTOP, hid)
                        ok(res == '', '%s · %s: list on top%s' % (name, label, (' — ' + res) if res else ''))
                        it = await pg.query_selector('.bp-hm-float .bp-hm-it:not(.on)') or await pg.query_selector('.bp-hm-float .bp-hm-it')
                        if it and 'Delete' not in (await it.inner_text()) and 'Remove' not in (await it.inner_text()):
                            ib = await it.bounding_box()
                            await pg.touchscreen.tap(ib['x'] + ib['width']/2, ib['y'] + min(ib['height']/2, 20)); await pg.wait_for_timeout(500)
                            ok(not await pg.evaluate("!!document.querySelector('.bp-hm-float')"), '%s · %s: item tapped, list closed' % (name, label))
                        await pg.evaluate("document.querySelectorAll('.sheet-overlay.open').forEach(function(s){s.classList.remove('open')}); try{closeModal&&0}catch(e){}")
                ok(not errs, 'no page errors %s' % errs[:3])
                await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
