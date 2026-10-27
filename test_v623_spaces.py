"""v6.2.3 — Spaces: photos on top as a stack that opens on request, checklist Open / Complete,
complete items are ticked AND lined through everywhere, ticks are instant and stay in view,
and Start / Completion date boxes are the same size. iPhone, iPad and Mac.
Run from repo root: python3 test_v623_spaces.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8896
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

PIC = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='40' height='30'><rect width='40' height='30' fill='%2355a'/></svg>"
SEED = """(PIC) => {
  var t = new Date().toISOString();
  DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', startDate:'2026-10-01', updatedAt:t }];
  DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }, { id:'r2', jobId:'j1', name:'Bath', updatedAt:t }];
  DB.punchlist = [
    { id:'p1', jobId:'j1', roomId:'r1', text:'Hang cabinets', done:false, updatedAt:t },
    { id:'p2', jobId:'j1', roomId:'r1', text:'Set sink', done:false, updatedAt:t },
    { id:'p3', jobId:'j1', roomId:'r1', text:'Paint ceiling', done:true, status:'Done', completedAt:t, updatedAt:t }];
  DB.photos = [0,1,2,3].map(function(i){ return { id:'ph'+i, jobId:'j1', roomId:'r1', src:PIC, date:t }; });
  try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} }
}"""
ROW_STATE = """(text) => {
  var n = [].find.call(document.querySelectorAll('.bp-cl-name, #bp-desk-checklist > div > div'), function(e){ return e.textContent.trim().indexOf(text) === 0 && e.offsetParent; });
  if (!n) return null;
  var row = n.closest('.bp-cl-row') || n.parentElement;
  var box = row.querySelector('.bp-cl-check, input[type=checkbox]');
  var ticked = box ? (box.tagName === 'INPUT' ? box.checked : !!box.querySelector('svg')) : false;
  return { ticked: ticked, lined: /line-through/.test(getComputedStyle(n).textDecorationLine) };
}"""

async def field(b, name, vp):
    print('\n' + name)
    ctx = await b.new_context(viewport=vp, has_touch=True, is_mobile=(name == 'iPhone'))
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 2, 3), name + ': on v6.2.3 or newer')
    await pg.evaluate(SEED, PIC); await pg.evaluate("openJobDetail('j1'); openRoomDetail('r1')"); await pg.wait_for_timeout(600)

    order = await pg.evaluate("""() => { var s = document.getElementById('s-room-detail'); var p = document.getElementById('bp-rd-photos'), c = document.getElementById('rd-checklist'), a = s.querySelector('.bp-act-row');
      return { photos: !!p, acts: !!a, photosAfterActs: !!(p && a && (a.compareDocumentPosition(p) & 4)), photosBeforeList: !!(p && c && (p.compareDocumentPosition(c) & 4)) }; }""")
    ok(order['photos'] and order['photosAfterActs'] and order['photosBeforeList'], name + ': photos sit on top, under the buttons, above the checklist ' + str(order))
    ok(await pg.evaluate("document.querySelectorAll('#bp-rd-photos .bp-pst-pile img').length") == 3, name + ': stack shows the top 3 photos')
    ok('Photos (4)' in await pg.inner_text('#bp-rd-photos .bp-pst'), name + ': stack shows the count')
    ok(not await pg.is_visible('#bp-rd-photos .photo-grid'), name + ': grid is closed until asked for')
    await pg.tap('#bp-rd-photos .bp-pst'); await pg.wait_for_timeout(200)
    ok(await pg.is_visible('#bp-rd-photos .photo-grid') and await pg.evaluate("document.querySelectorAll('#bp-rd-photos .photo-thumb').length") == 4, name + ': tap opens all 4 photos')
    await pg.tap('#bp-rd-photos .bp-pst'); await pg.wait_for_timeout(200)
    ok(not await pg.is_visible('#bp-rd-photos .photo-grid'), name + ': tap again closes it')
    ok(not await pg.evaluate("/undefined/.test(document.querySelector('#s-room-detail .detail-meta').textContent)"), name + ': no "undefined" under the space name')
    await pg.evaluate("openRoomDetail('r2')"); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate("/undefined/.test(document.querySelector('#s-room-detail .detail-meta').textContent)"), name + ': space with no type shows no "undefined"')
    ok(not await pg.evaluate("!!document.getElementById('bp-rd-photos')"), name + ': space with no photos shows no empty stack')
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(300)

    seg = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-clf-room .bp-seg button'), function(b){ return b.textContent + (b.classList.contains('on') ? '*' : ''); })")
    ok(seg == ['Open2*', 'Complete1'], name + ': Open / Complete buttons with counts, Open first ' + str(seg))
    ok(await pg.evaluate("!document.querySelector('#bp-clf-room .bp-pm')"), name + ': old Status menu is gone')
    ok(await pg.evaluate(ROW_STATE, 'Paint ceiling') is None, name + ': Open hides complete items')

    # tick with a real touch: instant, ticked + lined, stays in view
    box = await pg.query_selector('#cli-p1 .bp-cl-check'); bb = await box.bounding_box()
    t0 = await pg.evaluate("performance.now()")
    await pg.touchscreen.tap(bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2)
    st = await pg.evaluate(ROW_STATE, 'Hang cabinets'); dt = await pg.evaluate("performance.now()") - t0
    ok(st and st['ticked'] and st['lined'], name + ': ticked item shows a check AND a line through it ' + str(st))
    ok(dt < 150, name + ': tick shows in %d ms' % dt)
    ok(await pg.evaluate("DB.punchlist.find(function(n){ return n.id === 'p1'; }).done") is True, name + ': tick is saved on the item')
    await pg.wait_for_timeout(1600)
    st = await pg.evaluate(ROW_STATE, 'Hang cabinets')
    ok(st and st['ticked'] and st['lined'], name + ': ticked item stays in view on Open until you leave ' + str(st))
    seg = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-clf-room .bp-seg button'), function(b){ return b.textContent; })")
    ok(seg == ['Open1', 'Complete2'], name + ': counts update after a tick ' + str(seg))
    ok('33%' in await pg.inner_text('#s-room-detail .detail-header') or '67%' in await pg.inner_text('#s-room-detail .detail-header'), name + ': progress bar updates')
    await pg.tap('#bp-clf-room .bp-seg button[data-bp-show="done"]'); await pg.wait_for_timeout(200)
    a = await pg.evaluate(ROW_STATE, 'Paint ceiling'); c = await pg.evaluate(ROW_STATE, 'Hang cabinets')
    ok(a and a['ticked'] and a['lined'] and c and c['ticked'] and c['lined'], name + ': Complete shows every finished item, ticked and lined')
    ok(await pg.evaluate(ROW_STATE, 'Set sink') is None, name + ': Complete hides open items')
    await pg.tap('#bp-clf-room .bp-seg button[data-bp-show="open"]'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate(ROW_STATE, 'Hang cabinets') is None, name + ': after switching views, Open shows only open items')

    # job page and Punch tab: complete = ticked + lined
    await pg.evaluate("closeRoomDetail(); openJobDetail('j1')"); await pg.wait_for_timeout(500)
    jp = await pg.evaluate("""() => { var n = [].find.call(document.querySelectorAll('#s-job-detail div'), function(e){ return e.children.length === 0 && e.textContent.trim() === 'Paint ceiling' && e.offsetParent; });
      if (!n) return null; var row = n.parentElement.parentElement; var box = row.firstElementChild;
      return { lined: /line-through/.test(getComputedStyle(n).textDecorationLine), ticked: !!(box && box.querySelector('svg')) }; }""")
    ok(jp is None or (jp['ticked'] and jp['lined']), name + ': job page shows complete items ticked and lined ' + str(jp))
    row = await pg.evaluate("buildPunchItemRow(DB.punchlist.find(function(n){ return n.id === 'p3'; }))")
    ok('line-through' in row and '<polyline' in row, name + ': punch rows draw a done item ticked and lined')
    row = await pg.evaluate("buildPunchItemRow(DB.punchlist.find(function(n){ return n.id === 'p2'; }))")
    ok('line-through' not in row, name + ': open items are not lined')

    # job page draws its photos only when the Photos section is open
    n = await pg.evaluate("document.querySelectorAll('#jd-photos img').length")
    opened = await pg.evaluate("!!document.querySelector('#jd-stack .bp-acc[data-k=photos].open')")
    ok(opened or n == 0, name + ': job page does not draw photos while Photos is closed (%d drawn)' % n)
    await pg.evaluate("bpJobAccToggle('photos')"); await pg.wait_for_timeout(300)
    if not opened:
        ok(await pg.evaluate("document.querySelectorAll('#jd-photos img').length") == 4, name + ': opening Photos on the job page shows all 4')
        await pg.evaluate("bpJobAccToggle('photos')")

    # Started / Done cells and date boxes are the same size
    cells = await pg.evaluate("[].map.call(document.querySelectorAll('#jd-progress-toggles label.bp-jc-line'), function(l){ var r = l.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), l.textContent.trim()]; })")
    ok(len(cells) == 2 and cells[0][0] == cells[1][0] and cells[0][1] == cells[1][1], name + ': Started and Done cells are the same size ' + str(cells))
    ok(len(cells) == 2 and '10/01' in cells[0][2].replace('Oct 1', '10/01') or (len(cells) == 2 and any(ch.isdigit() for ch in cells[0][2])), name + ': Started shows its date like Done does')
    for sheet, ids in (("openAddJob ? openAddJob() : openSheet('sheet-add-job')", ('aj-start', 'aj-completion')), ("openAddRoom('j1')", ('ar-start', 'ar-completion')), ("openEditJob('j1')", ('ej-start', 'ej-completion'))):
        await pg.evaluate("document.querySelectorAll('.sheet.open,.sheet-overlay.open').forEach(function(s){ s.classList.remove('open'); })")
        await pg.evaluate(sheet); await pg.wait_for_timeout(400)
        await pg.evaluate("(ids) => { document.getElementById(ids[0]).value = '2026-10-26'; document.getElementById(ids[1]).value = ''; }", list(ids))
        sz = await pg.evaluate("(ids) => ids.map(function(i){ var s = getComputedStyle(document.getElementById(i)); var r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), s.appearance || s.webkitAppearance, s.minHeight]; })", list(ids))
        ok(sz[0][:2] == sz[1][:2] and sz[0][2] == 'none' and sz[0][3] != '0px', name + ': %s filled and empty are the same size %s' % ('/'.join(ids), sz))
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()

async def mac(b):
    print('\nMac')
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 2, 3), 'Mac: on v6.2.3 or newer')
    await pg.evaluate(SEED, PIC); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
    pos = await pg.evaluate("""() => { var p = document.getElementById('bp-mrd-photos'), s = document.getElementById('bp-mrd-seg'); return !!(p && s && (p.compareDocumentPosition(s) & 4)); }""")
    ok(pos, 'Mac: photos on top, above the checklist')
    ok('Photos (4)' in await pg.inner_text('#bp-mrd-photos'), 'Mac: stack shows the count')
    ok(not await pg.is_visible('#bp-mrd-photos .bp-pst-grid'), 'Mac: grid closed until asked for')
    await pg.click('#bp-mrd-photos .bp-pst'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("document.querySelectorAll('#bp-mrd-photos .bp-pst-grid img').length") == 4, 'Mac: click opens all 4 photos')
    seg = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-mrd-seg button'), function(b){ return b.textContent + (b.classList.contains('on') ? '*' : ''); })")
    ok(seg == ['Open2*', 'Complete1'], 'Mac: Open / Complete buttons with counts ' + str(seg))
    ok(await pg.evaluate(ROW_STATE, 'Paint ceiling') is None, 'Mac: Open hides complete items')
    await pg.evaluate("toggleCheckInRoomDetail('p1','r1')"); await pg.wait_for_timeout(400)
    st = await pg.evaluate(ROW_STATE, 'Hang cabinets')
    ok(st and st['ticked'] and st['lined'], 'Mac: ticked item stays in view, ticked and lined ' + str(st))
    await pg.click('#bp-mrd-seg button[data-bp-show="done"]'); await pg.wait_for_timeout(200)
    a = await pg.evaluate(ROW_STATE, 'Paint ceiling')
    ok(a and a['ticked'] and a['lined'] and await pg.evaluate(ROW_STATE, 'Set sink') is None, 'Mac: Complete shows finished items only, ticked and lined')
    await pg.evaluate("document.getElementById('modal-room-detail').remove(); showView('job-detail'); renderDesktopJobDetail('j1')"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#bp-mjd-photos .bp-pst-pile img').length") == 3 and await pg.evaluate("document.querySelectorAll('#bp-mjd-photos .bp-mjd-grid img').length") == 0, 'Mac job page: photos are a stack, grid not drawn until asked for')
    await pg.click('#bp-mjd-photos .bp-pst'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("document.querySelectorAll('#bp-mjd-photos .bp-mjd-grid img').length") == 4 and await pg.is_visible('#bp-mjd-photos .bp-mjd-grid'), 'Mac job page: click opens all 4 photos')
    await pg.evaluate("openNewJob()"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.getElementById('nj-start').value = '2026-10-26'")
    sz = await pg.evaluate("['nj-start','nj-completion'].map(function(i){ var r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
    ok(sz[0] == sz[1], 'Mac: start and completion boxes are the same size ' + str(sz))
    ok(not errs, 'Mac: no script errors ' + str(errs[:2]))
    await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await field(b, 'iPhone', {'width': 390, 'height': 844})
            await field(b, 'iPad', {'width': 1024, 'height': 1366})
            await mac(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
