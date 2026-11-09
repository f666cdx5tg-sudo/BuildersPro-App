"""v6.9.15 — Spaces: check / uncheck never makes the page jump, and checklist items can be deleted.
Command Center (iPad, Mac): a tick flips only its row (no rebuild), the window doesn't move a pixel in
Open or Complete view; Delete is in the Edit item window and the space reopens after; Update still updates.
iPhone: the slide-out Delete is on screen beside Move (it was hidden behind the next row) and works; an item
unchecked in Complete view stays put instead of vanishing a second later.
Run from repo root: python3 test_v6915_tick_delete.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8915
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};Object.defineProperty(navigator,'maxTouchPoints',{get:function(){return 5;}});"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }];
 DB.punchlist = []; for (var i = 1; i <= 24; i++) DB.punchlist.push({ id:'p'+i, jobId:'j1', roomId:'r1', text:'Item number '+i, done:i>16, updatedAt:t });
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
SAMPLE = """(idx) => new Promise(res => { var mo = document.getElementById('modal-room-detail'), out = [], t0 = performance.now();
  var cb = [].filter.call(document.querySelectorAll('#bp-desk-checklist input[type=checkbox]'), function(c){ return c.offsetParent; })[idx];
  var id = cb.getAttribute('onchange').match(/'([^']+)'/)[1], top0 = cb.getBoundingClientRect().top, s0 = mo.scrollTop;
  cb.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); cb.click();
  (function f(){ var m = document.getElementById('modal-room-detail');
    var c2 = document.querySelector('#bp-desk-checklist input[onchange*="\\'' + id + '\\'"]');
    out.push([m ? m.scrollTop - s0 : 999, c2 && c2.offsetParent ? Math.round(c2.getBoundingClientRect().top - top0) : 'gone']);
    if (performance.now() - t0 < 900) requestAnimationFrame(f); else res({ id: id, moves: out.filter(function(x){ return x[0] !== 0 || x[1] !== 0; }).slice(0, 4), done: (DB.punchlist.find(function(n){ return n.id === id; }) || {}).done }); })(); })"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def page(b, url, **kw):
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
    await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    return ctx, pg, errs
async def cc(b, name, **kw):
    print('\n' + name)
    ctx, pg, errs = await page(b, 'desktop.html', **kw)
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 15), name + ': on v6.9.15 or newer')
    await pg.evaluate("document.getElementById('modal-room-detail').scrollTop = 300")
    a = await pg.evaluate(SAMPLE, 3); ok(a['done'] and not a['moves'], name + ': check in Open view — nothing moves ' + str(a['moves']))
    a2 = await pg.evaluate(SAMPLE, 3); ok(not a2['done'] and not a2['moves'], name + ': uncheck it right away — nothing moves ' + str(a2['moves']))
    for k in range(3): await pg.evaluate(SAMPLE, 4 + k)
    seg = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-mrd-seg button'), function(b){ return b.textContent.trim(); })")
    ok(seg == ['13', '11'], name + ': counts follow every tick ' + str(seg))
    ok('Checklist (11/24)' in await pg.evaluate("document.getElementById('modal-room-detail').textContent"), name + ': header count follows')
    await pg.evaluate("bpMacSpaceShow('done')"); await pg.wait_for_timeout(250)
    await pg.evaluate("document.getElementById('modal-room-detail').scrollTop = 99999")
    c = await pg.evaluate(SAMPLE, 2); ok(not c['done'] and not c['moves'], name + ': uncheck in Complete view — nothing moves, row stays ' + str(c['moves']))
    c2 = await pg.evaluate(SAMPLE, 2); ok(c2['done'] and not c2['moves'], name + ': re-check it — still nothing moves ' + str(c2['moves']))
    # Edit window: Update still updates, Delete deletes
    await pg.evaluate("bpMacSpaceShow('open')"); await pg.wait_for_timeout(200)
    await pg.locator('#bp-desk-checklist > div:visible').first.locator('button').first.click(); await pg.wait_for_timeout(500)
    ok(await pg.is_visible('#bp-ec-del'), name + ': Edit item window has Delete')
    ok((await pg.evaluate("document.querySelector('#modal-new-check .btn:not(.btn-ghost)').textContent")).strip() == 'Update Item', name + ': …and Update is still Update (not Add — no duplicates)')
    n0 = await pg.evaluate("DB.punchlist.length")
    await pg.fill('#nc2-text', 'Renamed item'); await pg.click('#modal-new-check .btn:not(.btn-ghost)'); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("DB.punchlist.length") == n0 and await pg.evaluate("DB.punchlist.some(function(n){ return n.text === 'Renamed item'; })"), name + ': Update renames, no extra item')
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(400)
    await pg.locator('#bp-desk-checklist > div:visible').first.locator('button').first.click(); await pg.wait_for_timeout(500)
    victim = await pg.evaluate("document.getElementById('modal-new-check').dataset.bpEditId")
    await pg.click('#bp-ec-del'); await pg.wait_for_timeout(800)
    ok(await pg.evaluate("DB.punchlist.length") == n0 - 1 and not await pg.evaluate("DB.punchlist.some(function(n){ return n.id === '%s'; })" % victim), name + ': Delete removes the item')
    ok(await pg.evaluate("(DB.recycle || []).some(function(r){ return r.rec && r.rec.id === '%s'; })" % victim), name + ': …and it is in Recently Deleted')
    ok(await pg.evaluate("!!document.getElementById('modal-room-detail') && !document.querySelector('#bp-desk-checklist input[onchange*=\"\\'%s\\'\"]')" % victim), name + ': the space opens again, item gone')
    await pg.evaluate("openNewCheckItem('j1','r1')"); await pg.wait_for_timeout(300)
    ok(not await pg.is_visible('#bp-ec-del'), name + ': New item window has no Delete')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def phone(b):
    name = 'iPhone'; print('\n' + name)
    ctx, pg, errs = await page(b, 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    cdp = await ctx.new_cdp_session(pg)
    row = pg.locator('#s-room-detail .bp-cl-row').first; bb = await row.bounding_box()
    await row.evaluate("e => e.scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(200); bb = await row.bounding_box()
    x, y = bb['x'] + bb['width'] * 0.55, bb['y'] + bb['height'] / 2
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
    for i in range(1, 11): await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x - i * 25, 'y': y}]}); await pg.wait_for_timeout(16)
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []}); await pg.wait_for_timeout(500)
    g = await pg.evaluate("""(function(){ var d = document.querySelector('#s-room-detail .bp-pill-del'), r = d.closest('.bp-cl-row'), q = d.getBoundingClientRect(), rr = r.getBoundingClientRect();
      var h = document.elementFromPoint((q.left + q.right) / 2, (q.top + q.bottom) / 2);
      return { inside: q.top >= rr.top - 1 && q.bottom <= rr.bottom + 1, onScreen: q.right <= innerWidth, hit: !!(h && h.closest('.bp-pill-del')) }; })()""")
    ok(g['inside'] and g['onScreen'] and g['hit'], name + ': slide-out Delete is on screen beside Move, on screen, nothing covering it ' + str(g))
    n0 = await pg.evaluate("DB.punchlist.length")
    await pg.click('#s-room-detail .bp-pill-del'); await pg.wait_for_timeout(300)
    await pg.click('#bp-sw-confirm .bp-sw-yes'); await pg.wait_for_timeout(1500)
    ok(await pg.evaluate("DB.punchlist.length") == n0 - 1, name + ': Delete → confirm removes the item')
    await pg.evaluate("bpSpaceShow('done','room','r1')"); await pg.wait_for_timeout(500)
    tgt = await pg.evaluate("(function(){ var r = document.querySelectorAll('#s-room-detail .bp-cl-row')[1]; return r.getAttribute('data-cl-id'); })()")
    top0 = await pg.evaluate("document.getElementById('cli-%s').getBoundingClientRect().top" % tgt)
    await pg.evaluate("toggleChecklistItem('%s')" % tgt); await pg.wait_for_timeout(1800)
    st = await pg.evaluate("(function(){ var r = document.getElementById('cli-%s'); return r ? [Math.round(r.getBoundingClientRect().top), !!r.offsetParent] : null; })()" % tgt)
    ok(st and st[1] and abs(st[0] - top0) < 2, name + ': unchecked in Complete view, it stays where it was after the list redraws %s→%s' % (round(top0), st))
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await cc(b, 'iPad Command Center', viewport={'width': 1180, 'height': 820}, user_agent=IPAD, has_touch=True)
            await cc(b, 'Mac Command Center', viewport={'width': 1440, 'height': 900})
            await phone(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
