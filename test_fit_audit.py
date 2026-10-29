"""BuildersPro — "everything stays in its cell" audit (v6.5.0).
Opens every main screen and sheet of the field app (iPhone sizes, every text size, light + dark) and the
Command Center (Mac + small laptop width) with realistic, long data, and reports any text that is cut off
inside its box or spills past the box it sits in, or pushes the page sideways.
Run from repo root: python3 test_fit_audit.py [--verbose]      Exit 0 = nothing out of its cell."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8950
VERBOSE = '--verbose' in sys.argv
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')

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

AUDIT = r"""(scope) => {
  var out = [], seen = new Set();
  var root = scope ? document.querySelector(scope) : document.body; if (!root) return [];
  var vw = document.documentElement.clientWidth;
  function vis(e){ var r = e.getBoundingClientRect(); if (!r.width || !r.height) return false; var c = getComputedStyle(e); return c.visibility !== 'hidden' && c.display !== 'none' && +c.opacity !== 0; }
  function boxOf(e){
    for (var a = e.parentElement; a && a !== document.body; a = a.parentElement) {
      var c = getComputedStyle(a);
      if (a.matches('button, select, input, .card, [data-onsite], .bp-area-box, .bp-seg, .bp-pm, .bp-selbtn, .kpi, .bp-kpi, .tb-btn, .ni, .bp-cl-row, [id^="cli-"]')) return a;
      if ((c.borderTopWidth !== '0px' && c.borderTopStyle !== 'none' && parseFloat(c.borderTopWidth) > 0 && c.borderRadius !== '0px') || (c.backgroundColor !== 'rgba(0, 0, 0, 0)' && c.borderRadius !== '0px')) return a;
    }
    return null;
  }
  function name(e){ var s = e.tagName.toLowerCase(); if (e.id) s += '#' + e.id; var c = (typeof e.className === 'string' ? e.className : '').trim().split(/\s+/).slice(0,2).join('.'); if (c) s += '.' + c; return s; }
  var els = root.querySelectorAll('*');
  for (var i = 0; i < els.length; i++) {
    var e = els[i];
    if (!vis(e) || e.closest('svg, script, style, canvas, video, [aria-hidden="true"], .bp-fit-ok')) continue;
    var txt = ''; for (var n = e.firstChild; n; n = n.nextSibling) if (n.nodeType === 3) txt += n.nodeValue;
    txt = txt.replace(/\s+/g, ' ').trim();
    if (e.tagName === 'SELECT') txt = (e.options[e.selectedIndex] || {}).text || '';
    if (!txt) continue;
    var c = getComputedStyle(e), r = e.getBoundingClientRect();
    var problems = [];
    if ((c.overflowX === 'hidden' || c.overflowX === 'clip' || c.textOverflow === 'ellipsis' || e.tagName === 'SELECT') && e.scrollWidth > e.clientWidth + 2) problems.push('cut off');
    var sideScroll = false; for (var a = e.parentElement; a && a !== document.body; a = a.parentElement) { var ox = getComputedStyle(a).overflowX; if ((ox === 'auto' || ox === 'scroll') && a.scrollWidth > a.clientWidth + 2) { sideScroll = true; break; } }
    if (sideScroll) continue;
    if (e.tagName !== 'SELECT' && !problems.length) {
      var rg = document.createRange(); rg.selectNodeContents(e); var tr = rg.getBoundingClientRect();
      var box = boxOf(e);
      if (box && tr.width) { var b = box.getBoundingClientRect(); if (tr.right > b.right + 1.5 || tr.left < b.left - 1.5) problems.push('spills out of ' + name(box)); }
      if (tr.right > vw + 1) problems.push('past the screen edge');
    }
    if (!problems.length) continue;
    var key = name(e) + '|' + txt.slice(0, 40) + '|' + problems.join();
    if (seen.has(key)) continue; seen.add(key);
    out.push({ el: name(e), text: txt.slice(0, 60), problems: problems, w: Math.round(r.width) });
  }
  if (document.documentElement.scrollWidth > vw + 1) out.push({ el: 'page', text: '', problems: ['page scrolls sideways'], w: document.documentElement.scrollWidth });
  return out;
}"""

FIELD_STEPS = [
  ('Home', "showScreen('s-home')", None),
  ('Jobs', "showScreen('s-jobs')", '#s-jobs'),
  ('Job page', "openJobDetail('j1')", '#s-job-detail'),
  ('Spaces', "showScreen('s-rooms')", '#s-rooms'),
  ('Space', "openRoomDetail('r3')", '#s-room-detail'),
  ('Punch areas', "window._bpPunchJob='j1'; showScreen('s-punch')", '#s-punch'),
  ('Punch all open', "showScreen('s-punch'); var b=document.querySelector('#punch-count .bp-pc.o'); if (b) b.click();", '#s-punch'),
  ('Punch all done', "try{bpClosePunchArea()}catch(e){} var b=document.querySelector('#punch-count .bp-pc.d'); if (b) b.click();", '#s-punch'),
  ('Photos', "showScreen('s-photos')", '#s-photos'),
  ('Money', "showScreen('s-finance'); try{ setFinanceTab('overview') }catch(e){}", '#s-finance'),
  ('Money: spending', "try{ setFinanceTab('spending') }catch(e){}", '#s-finance'),
  ('Money: invoices', "try{ setFinanceTab('invoices') }catch(e){}", '#s-finance'),
  ('Calendar', "showScreen('s-calendar')", '#s-calendar'),
  ('Time', "showScreen('s-time')", '#s-time'),
  ('Money check', "showScreen('s-home'); bpMoneyCheck('j1')", '#bp-mcheck'),
  ('Shopping list', "bpMoneyCheckClose(); try{ bpOpenShop('j1') }catch(e){}", '#bp-shop'),
  ('Phone book', "var s=document.getElementById('bp-shop'); if(s) s.remove(); try{ bpPhoneBookOpen() }catch(e){}", None),
  ('AI assistant', "document.querySelectorAll('.sheet-overlay.open').forEach(function(o){o.classList.remove('open')}); try{ bpAISettings() }catch(e){}", '#bp-ai-settings'),
  ('Side menu', "var a=document.getElementById('bp-ai-settings'); if(a) a.remove(); document.body.classList.add('bp-drawer-open')", '#bp-drawer'),
]
DESK_VIEWS = ['dashboard', 'jobs', 'rooms', 'punchlist', 'photos', 'finance', 'eod', 'estimates', 'calendar', 'contacts', 'documents', 'time', 'sync']

async def run_field(b, width, zoom, theme, report):
    ctx = await b.new_context(viewport={'width': width, 'height': 900}, is_mobile=True, has_touch=True)
    pg = await ctx.new_page()
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2200)
    await pg.evaluate("(a) => { document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined; localStorage.setItem('bp_zoom', a[0]); try { bpApplyZoom(); } catch(e){} document.documentElement.setAttribute('data-theme', a[1]); }", [str(zoom), theme])
    await pg.evaluate(SEED)
    for label, js, scope in FIELD_STEPS:
        try:
            await pg.evaluate("() => { try { " + js + " } catch(e) { console.warn(e); } }")
            await pg.wait_for_timeout(650)
            await pg.evaluate("document.querySelectorAll('.bp-tip,.bp-toast,#toast,.toast').forEach(function(e){e.remove()})")
            await pg.wait_for_timeout(400)   # let the page's own fit pass settle after the last redraw
            for it in await pg.evaluate(AUDIT, scope):
                report.setdefault((label, it['el'], it['text'], ', '.join(it['problems'])), []).append('%dpx %s %s' % (width, zoom, theme))
        except Exception as ex:
            report.setdefault((label, 'ERROR', str(ex)[:80], ''), []).append('%dpx %s' % (width, zoom))
    await ctx.close()

async def run_desk(b, width, theme, report):
    ctx = await b.new_context(viewport={'width': width, 'height': 900})
    pg = await ctx.new_page()
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2600)
    await pg.evaluate("(t) => { document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined; document.documentElement.setAttribute('data-theme', t); }", theme)
    await pg.evaluate(SEED)
    for v in DESK_VIEWS:
        try:
            await pg.evaluate("(v) => { try { showView(v); } catch(e){} }", v); await pg.wait_for_timeout(650)
            for it in await pg.evaluate(AUDIT, None):
                report.setdefault(('Mac ' + v, it['el'], it['text'], ', '.join(it['problems'])), []).append('%dpx %s' % (width, theme))
        except Exception as ex:
            report.setdefault(('Mac ' + v, 'ERROR', str(ex)[:80], ''), []).append('%dpx' % width)
    await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    report = {}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for width in (375, 402, 440):
                for zoom in (1.0, 1.15, 1.3, 1.45):
                    await run_field(b, width, zoom, 'dark' if zoom in (1.15, 1.45) else 'light', report)
            await run_field(b, 820, 1.15, 'light', report)      # iPad
            for width in (1280, 1440):
                await run_desk(b, width, 'light' if width == 1440 else 'dark', report)
            await b.close()
    finally:
        srv.terminate()
    rows = sorted(report.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    for (screen, el, text, prob), where in rows:
        print('  OUT  %-18s %-38s %-30s %s  [%s%s]' % (screen, el[:38], ('"' + text + '"')[:30], prob, where[0], (' +%d more' % (len(where) - 1)) if len(where) > 1 else ''))
        if VERBOSE: print('        ', where)
    print('\n%d things out of their cells' % len(rows))
    sys.exit(1 if rows else 0)
asyncio.run(main())
