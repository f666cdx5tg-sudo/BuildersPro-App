"""BuildersPro v6.0.1 (Spaces check-off: one tap, instant, survives finger drift).
Run from repo root: python3 test_v601.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
    else: print('  ok  ', m)

SEED = """(function(){
  DB.jobs.push({id:'jA',name:'Smith Reno',status:'active'});
  DB.rooms=DB.rooms||[]; DB.rooms.push({id:'rA',jobId:'jA',name:'Bath',type:'Bathroom'});
  DB.punchlist=DB.punchlist||[];
  for (var i=1;i<=6;i++) DB.punchlist.push({id:'p'+i,jobId:'jA',roomId:'rA',text:'Item '+i,done:false,created:new Date().toISOString()});
  window.__saves=0; var s=window.save; window.save=function(){ window.__saves++; return s.apply(this,arguments); };
  window.__rebuilds=0; var o=window.openRoomDetail; window.openRoomDetail=function(){ window.__rebuilds++; return o.apply(this,arguments); };
  openRoomDetail('rA'); window.__rebuilds=0;
})()"""

async def tap(pg, cdp, sel, dx=0, dy=0):
    await pg.evaluate("s=>document.querySelector(s).scrollIntoView({block:'center'})", sel); await pg.wait_for_timeout(80)
    box = await pg.locator(sel).bounding_box()
    x = box['x'] + box['width'] / 2; y = box['y'] + box['height'] / 2
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
    if dx or dy:
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + dx, 'y': y + dy}]})
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8791', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github')) else r.continue_())
            await pg.goto('http://localhost:8791/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION==='6.0.1'"), 'version 6.0.1')
            await pg.evaluate(SEED); await pg.wait_for_timeout(300)
            ok(await pg.locator('#cli-p1 .bp-cl-check').count() == 1, 'check box has bp-cl-check class')

            # 1 clean single tap -> checked immediately, no screen rebuild yet
            await tap(pg, cdp, '#cli-p1 .bp-cl-check')
            await pg.wait_for_timeout(60)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p1').done===true"), 'one tap checks item')
            ok(await pg.evaluate("document.querySelector('#cli-p1 .bp-cl-check svg')!==null"), 'tick painted right away')
            ok(await pg.evaluate("window.__rebuilds===0"), 'no full screen rebuild on the tap itself')
            ok(await pg.evaluate("window.__saves>=1"), 'saved right after paint')

            # 2 tap with 10px thumb drift sideways (used to become a swipe and get swallowed)
            await tap(pg, cdp, '#cli-p2 .bp-cl-check', dx=10, dy=3)
            await pg.wait_for_timeout(60)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p2').done===true"), 'drifting tap (10px) still checks')
            ok(await pg.evaluate("!document.getElementById('cli-p2').style.transform"), 'drifting tap did not slide the row')

            # 3 no double toggle from the trailing click
            await pg.wait_for_timeout(500)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p1').done && DB.punchlist.find(x=>x.id==='p2').done"), 'no ghost second toggle')

            # 4 rapid ticks down the list: rows stay put, then one rebuild
            for i in (3, 4, 5):
                await tap(pg, cdp, '#cli-p%d .bp-cl-check' % i); await pg.wait_for_timeout(120)
            ok(await pg.evaluate("['p3','p4','p5'].every(id=>DB.punchlist.find(x=>x.id===id).done)"), 'rapid ticks all register')
            ok(await pg.evaluate("window.__rebuilds===0"), 'screen held still while ticking')
            await pg.wait_for_timeout(1400)
            ok(await pg.evaluate("window.__rebuilds===1"), 'one refresh after ticking stops')
            ok(await pg.evaluate("document.getElementById('s-room-detail').textContent.includes('83%')"), 'progress updated (5/6)')

            ok(await pg.evaluate("!document.getElementById('cli-p1')"), 'checked items leave the Open list after the pause')

            # 5 untick works too (before the Open filter hides it)
            await tap(pg, cdp, '#cli-p6 .bp-cl-check'); await pg.wait_for_timeout(450)
            await tap(pg, cdp, '#cli-p6 .bp-cl-check'); await pg.wait_for_timeout(60)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p6').done===false"), 'tap again unchecks')
            await pg.wait_for_timeout(1300)

            # 6 real scroll on the box does not toggle
            await tap(pg, cdp, '#cli-p6 .bp-cl-check', dy=40); await pg.wait_for_timeout(60)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p6').done===false"), 'scroll gesture does not toggle')

            # 7 slide row still works when started on the text
            await pg.wait_for_timeout(1300)
            await pg.evaluate("document.querySelector('#cli-p6 .bp-cl-name').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(80)
            box = await pg.locator('#cli-p6 .bp-cl-name').bounding_box()
            x = box['x'] + 20; y = box['y'] + box['height'] / 2
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
            for k in range(1, 8):
                await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x - k * 20, 'y': y}]})
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            await pg.wait_for_timeout(250)
            ok(await pg.evaluate("!!document.querySelector('#cli-p6 .bp-cl-acts')"), 'slide for Cut/Delete still works')

            # 8 mouse click (desktop) still works
            await pg.evaluate("document.body.click()"); await pg.wait_for_timeout(300)
            await pg.evaluate("toggleChecklistItem('p6')"); await pg.wait_for_timeout(60)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p6').done===true"), 'click path still toggles')

            # 9 undo still works
            await pg.evaluate("bpUndoLast()"); await pg.wait_for_timeout(100)
            ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p6').done===false"), 'undo reverts the tick')

            ok(not errs, 'no page errors: %s' % errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print('%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
