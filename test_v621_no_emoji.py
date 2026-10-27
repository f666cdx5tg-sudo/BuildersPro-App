"""v6.2.1 — no emoji anywhere, line icons only, on iPhone, iPad and Mac.
Seeds a realistic job (every space type, punch items, subs with thumbs ratings, money, permits,
estimates, notes, security, recently-deleted items, offline/sync states), opens every screen and
the common sheets on each device, and scans every visible text node for a raw emoji. Also checks
that pop-up messages and box hints never show an emoji.
Run from repo root: python3 test_v621_no_emoji.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8892
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

SPACES = ["(F) Bathroom","(B) Bathroom","Bedroom","front Roof","Gutters","Chimney","Front Door","Main Entrance","Driveway","Front Steps",
          "Basement/ mechanical","Foyer","2nd Fl.Stairs","Water Service","handicap ramp","Kitchen","Family Room","Laundry","Hallway","Boiler Room"]
SEED = """(S) => {
  var t = new Date().toISOString();
  DB.jobs = [{ id:'j1', name:'N. Peach St', client:'Shelden Washington', address:'1536 N. Peach St', clientEmail:'s@x.com', clientPhone:'2015550123', contract:45000, status:'Active',
               security:[{ id:'s1', kind:'wifi', label:'Router', user:'PeachNet', secret:'x' }], updatedAt:t }];
  DB.rooms = S.map(function(n, i){ return { id:'r'+i, jobId:'j1', name:n, level: i < 3 ? 'Basement' : 'Level 1', updatedAt:t }; });
  DB.punchlist = S.map(function(n, i){ return { id:'p'+i, jobId:'j1', roomId:'r'+i, text:'Item '+i, done: i % 3 === 0, status: i % 3 === 0 ? 'Done' : 'Open', updatedAt:t }; });
  DB.contractors = [{ id:'c1', jobId:'j1', name:'Ever', company:'Ever LLC', trade:'Plumbing', rating:'up', thumb:'up', updatedAt:t }, { id:'c2', jobId:'j1', name:'Dom', trade:'Electrical', rating:'down', thumb:'down', updatedAt:t }];
  DB.payments = [{ id:'pay1', contractorId:'c1', amount:500, date:'2026-10-20', updatedAt:t }];
  DB.expenses = [{ id:'e1', jobId:'j1', desc:'PEX', amount:120, category:'Materials', date:'2026-10-20', updatedAt:t }];
  DB.invoices = [{ id:'i1', jobId:'j1', number:'INV-1', amount:5000, status:'Sent', date:'2026-10-20', updatedAt:t }];
  DB.permits = [{ id:'pm1', jobId:'j1', trade:'Plumbing', status:'Applied', updatedAt:t }];
  DB.estimates = [{ id:'es1', title:'Bath', client:'C', status:'Draft', lineItems:[{ desc:'x', qty:1, price:100 }], updatedAt:t }];
  DB.appointments = [{ id:'a1', jobId:'j1', date: t.slice(0,10), time:'09:30', title:'Inspection', type:'Inspection', updatedAt:t }];
  DB.reports = [{ id:'rp1', jobId:'j1', date: t.slice(0,10), summary:'EOD', updatedAt:t }];
  DB.jobNotes = [{ id:'n1', jobId:'j1', text:'Note', created:t, updatedAt:t }];
  DB.shopping = [{ id:'sh1', jobId:'j1', item:'PEX', qty:2, unit:'roll', price:40, bought:false, updatedAt:t }];
  DB.recycle = [{ id:'rc_photos_x', coll:'photos', rec:{ id:'x', jobId:'j1' }, label:'(untitled) · N. Peach St', deletedAt:t }];
  try { bpSave(); } catch(e) {}
  try { bpSetActiveJob('j1', true); } catch(e) {}
}"""
SCAN = """() => {
  var re = /(?![\\u00A9\\u00AE\\u203C\\u2049\\u2122\\u2190-\\u21FF\\u2713-\\u2718\\u2B05-\\u2B07])\\p{Extended_Pictographic}/u;
  var out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), n;
  while ((n = w.nextNode())) {
    var p = n.parentElement; if (!p) continue;
    if (p.closest('script,style,textarea,option,select,title,noscript,.bp-ic-t')) continue;
    if (!p.offsetParent && getComputedStyle(p).position !== 'fixed') continue;
    var cs = getComputedStyle(p); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    if (re.test(n.nodeValue)) out.push(n.nodeValue.trim().slice(0, 50) + '  ⟵ ' + (p.closest('button,.card,div') || p).className.slice(0, 30));
  }
  var ph = [].filter.call(document.querySelectorAll('[placeholder]'), function(e){ return re.test(e.getAttribute('placeholder')); }).map(function(e){ return 'placeholder: ' + e.getAttribute('placeholder'); });
  return out.concat(ph);
}"""

async def settle(pg, ms=700):
    await pg.wait_for_timeout(ms)

async def check_device(b, name, page, vp, touch, steps):
    ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=(name == 'iPhone'))
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    msgs = []
    async def dlg(d): msgs.append(d.message); await d.dismiss()
    pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, page)); await settle(pg, 3000)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 2, 1), name + ': on v6.2.1 or newer')
    await pg.evaluate(SEED, SPACES); await settle(pg, 500)
    print('\n' + name)
    for label, js in steps:
        try:
            await pg.evaluate(js); await settle(pg)
        except Exception as e:
            ok(False, '%s: could not open %s (%s)' % (name, label, str(e)[:80])); continue
        found = await pg.evaluate(SCAN)
        ok(not found, '%s — %s: no raw emoji %s' % (name, label, found[:4] if found else ''))
        try: await pg.evaluate("document.querySelectorAll('.modal-overlay.open').forEach(function(m){ m.classList.remove('open'); }); ['bp-notes-ov','bp-sec-modal','modal-estimate'].forEach(function(id){ var e=document.getElementById(id); if(e) e.remove(); }); try{ closeSheet && document.querySelectorAll('.sheet.open,.sheet-overlay.open').forEach(function(s){ s.classList.remove('open'); }); }catch(e){}")
        except Exception: pass
    # pop-ups can't hold icons: emoji are taken out
    await pg.evaluate("confirm('⚠️ Delete this photo? 🗑'); alert('✅ Saved 💡 tip');")
    await settle(pg, 300)
    ok(msgs[-2:] == ['Delete this photo? ', 'Saved tip'], name + ': pop-up messages have no emoji ' + json.dumps(msgs[-2:], ensure_ascii=False))
    await pg.evaluate("var i = document.createElement('input'); i.id = 'ph-t'; i.placeholder = '🔍 Search jobs'; document.body.appendChild(i);"); await settle(pg, 500)
    ok(await pg.evaluate("document.getElementById('ph-t').placeholder") == 'Search jobs', name + ': hint text in boxes has no emoji')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()

FIELD = [('Home', "showScreen('s-home')"), ('Jobs', "showScreen('s-jobs')"), ('Job page', "openJobDetail('j1')"),
         ('Spaces', "showScreen('s-rooms')"), ('Photos', "showScreen('s-photos')"), ('Punch', "showScreen('s-punch')"),
         ('Money', "showScreen('s-finance')"), ('Calendar', "showScreen('s-calendar')"), ('Search', "showScreen('s-search')"),
         ('Time clock', "showScreen('s-time')"), ('Sync', "openSync()"), ('Notes', "bpOpenNotes('j1')"),
         ('Security open', "openJobDetail('j1'); bpSecToggle('j1')"), ('Space page', "typeof openRoomDetail==='function' && openRoomDetail('r1')")]
MAC = [('Home', "showView('dashboard')"), ('Calendar', "showView('calendar')"), ('Jobs', "showView('jobs')"), ('Estimates', "showView('estimates')"),
       ('Time Clock', "showView('time')"), ('Spaces', "showView('rooms')"), ('Photos', "showView('photos')"), ('Punch', "showView('punchlist')"),
       ('Documents', "showView('documents')"), ('EOD Reports', "showView('eod')"), ('Money', "showView('finance')"), ('Phone book', "showView('contacts')"),
       ('Archived Jobs', "showView('archive')"), ('Sync', "showView('sync')"), ('Job page', "openJobDetail('j1')"),
       ('Security open', "openJobDetail('j1'); bpSecToggle('j1')"), ('Notes', "bpOpenNotes('j1')"), ('New estimate', "openNewEstimateDesktop()")]

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await check_device(b, 'iPhone', 'index.html', {'width': 390, 'height': 844}, True, FIELD)
            await check_device(b, 'iPad', 'index.html', {'width': 1024, 'height': 1366}, True, FIELD)
            await check_device(b, 'Mac', 'desktop.html', {'width': 1440, 'height': 900}, False, MAC)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
