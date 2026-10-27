"""v6.2.6 — Punch: tap a heading to see open or done (field app + Mac).
1. OPEN / DONE on a space card opens that space showing just those items.
2. "N open" / "N done" under the Punch title shows every open / done item on the job.
3. Inside a space, tapping its name flips Open <-> Complete.
Run from repo root: python3 test_v626_punch_headings.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8909
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

SEED = """() => {
  var t = new Date().toISOString();
  DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', updatedAt:t }];
  DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', level:'Level 1', updatedAt:t }, { id:'r2', jobId:'j1', name:'Bath', type:'Bathroom', level:'Level 1', updatedAt:t }];
  DB.punchlist = [
    { id:'p1', jobId:'j1', roomId:'r1', text:'KOPEN-1', done:false, updatedAt:t },
    { id:'p2', jobId:'j1', roomId:'r1', text:'KDONE-2', done:true, status:'Done', completedAt:t, updatedAt:t },
    { id:'p3', jobId:'j1', roomId:'r1', text:'KDONE-3', done:true, status:'Done', completedAt:t, updatedAt:t },
    { id:'p4', jobId:'j1', roomId:'r2', text:'BOPEN-4', done:false, updatedAt:t },
    { id:'p5', jobId:'j1', roomId:'r2', text:'BDONE-5', done:true, status:'Done', completedAt:t, updatedAt:t }];
  try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} }
  try { bpSetActiveJob('j1', true); } catch(e){}
}"""
VIS = """() => { var out = []; var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), n;
  while ((n = w.nextNode())) { var v = n.nodeValue.trim(); if (!/^[KB](OPEN|DONE)-\\d$/.test(v)) continue; var p = n.parentElement;
    if (!p.offsetParent && getComputedStyle(p).position !== 'fixed') continue; var tr = p.closest('tr'); if (tr && getComputedStyle(tr).display === 'none') continue; out.push(v); }
  return Array.from(new Set(out)).sort(); }"""

async def field(b):
    print('\niPhone')
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 2, 6), 'iPhone: on v6.2.6 or newer')
    await pg.evaluate(SEED); await pg.evaluate("showScreen('s-punch')"); await pg.wait_for_timeout(600)

    pc = await pg.inner_text('#punch-count')
    ok('2 open' in pc and '3 done' in pc and await pg.evaluate("document.querySelectorAll('#punch-count .bp-pc').length") == 2, 'iPhone: "2 open · 3 done" are two tappable words (%s)' % pc)
    await pg.tap('#punch-count .bp-pc.o'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate(VIS) == ['BOPEN-4', 'KOPEN-1'], 'iPhone: tap "open" shows every open item on the job %s' % await pg.evaluate(VIS))
    ok('All open items' in await pg.inner_text('#punch-body'), 'iPhone: the list is labelled "All open items"')
    await pg.evaluate("bpClosePunchArea()"); await pg.wait_for_timeout(400)
    await pg.tap('#punch-count .bp-pc.d'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate(VIS) == ['BDONE-5', 'KDONE-2', 'KDONE-3'], 'iPhone: tap "done" shows every done item %s' % await pg.evaluate(VIS))
    await pg.evaluate("bpClosePunchArea()"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("document.querySelectorAll('#s-punch .bp-area-box').length") >= 2, 'iPhone: back shows the space cards again')

    n = await pg.evaluate("document.querySelectorAll('#s-punch .bp-area-box .bp-tapstat').length")
    ok(n >= 4, 'iPhone: OPEN and DONE on each space card are tappable (%d)' % n)
    await pg.tap('#s-punch .bp-area-box[data-bp-name="Kitchen"] .bp-tapstat[data-show="done"]'); await pg.wait_for_timeout(600)
    ok(await pg.evaluate(VIS) == ['KDONE-2', 'KDONE-3'], 'iPhone: Kitchen DONE shows only Kitchen\'s done items %s' % await pg.evaluate(VIS))
    await pg.evaluate("closeRoomDetail && document.getElementById('s-room-detail') ? closeRoomDetail() : bpClosePunchArea(); showScreen('s-punch'); bpClosePunchArea()"); await pg.wait_for_timeout(500)
    await pg.tap('#s-punch .bp-area-box[data-bp-name="Kitchen"] .bp-tapstat[data-show="open"]'); await pg.wait_for_timeout(600)
    ok(await pg.evaluate(VIS) == ['KOPEN-1'], 'iPhone: Kitchen OPEN shows only Kitchen\'s open items %s' % await pg.evaluate(VIS))

    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
    ok(await pg.evaluate(VIS) == ['KOPEN-1'], 'iPhone: space starts on Open')
    await pg.tap('#s-room-detail .detail-title'); await pg.wait_for_timeout(400)
    ok(await pg.evaluate(VIS) == ['KDONE-2', 'KDONE-3'], 'iPhone: tap the space name → Complete %s' % await pg.evaluate(VIS))
    await pg.tap('#s-room-detail .detail-title'); await pg.wait_for_timeout(400)
    ok(await pg.evaluate(VIS) == ['KOPEN-1'], 'iPhone: tap it again → Open')
    ok(not errs, 'iPhone: no script errors ' + str(errs[:2]))
    await ctx.close()

async def mac(b):
    print('\nMac')
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    await pg.evaluate(SEED); await pg.evaluate("showView('punchlist')"); await pg.wait_for_timeout(600)
    ok(await pg.evaluate("document.querySelectorAll('#punchlist-sub .bp-pc').length") == 2, 'Mac: "N open · N done" are clickable (%s)' % await pg.inner_text('#punchlist-sub'))
    await pg.click('#punchlist-sub .bp-pc >> nth=0'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate(VIS) == ['BOPEN-4', 'KOPEN-1'], 'Mac: click "open" shows every open item %s' % await pg.evaluate(VIS))
    await pg.evaluate("bpClosePunchArea()"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("document.querySelectorAll('#view-punchlist .bp-area-box .bp-tapstat').length") >= 4, 'Mac: OPEN / DONE on space cards are clickable')
    await pg.click('#view-punchlist .bp-area-box[data-bp-name="Kitchen"] .bp-tapstat[data-show="done"]'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate(VIS) == ['KDONE-2', 'KDONE-3'], 'Mac: Kitchen DONE shows only Kitchen\'s done items %s' % await pg.evaluate(VIS))
    await pg.click('#bp-desk-punch-header .bp-pshow[data-show="open"]'); await pg.wait_for_timeout(400)
    ok(await pg.evaluate(VIS) == ['KOPEN-1'], 'Mac: click "open" in the space header switches to open %s' % await pg.evaluate(VIS))
    await pg.evaluate("bpClosePunchArea()"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("window._bpDF.show") == 'all', 'Mac: leaving the space resets to all')
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
    await pg.click('#modal-room-detail .modal-title'); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelector('#bp-mrd-seg button.on').getAttribute('data-bp-show')") == 'done', 'Mac: click the space name → Complete')
    ok(not errs, 'Mac: no script errors ' + str(errs[:2]))
    await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await field(b); await mac(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
