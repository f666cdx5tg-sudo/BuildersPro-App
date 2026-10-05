"""BuildersPro v3.48 area header: Room/Area switch under the icon, icon-only Add Item/List/Photo, no duplicate buttons.
Run from the repo root: python3 test_v348.py  (needs playwright + chromium). Exit code 0 = all pass.
Reuses the seed data + page helper from test_v347.py."""
import sys, os, subprocess, time, asyncio

REPO = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(REPO, 'test_v347.py'), encoding='utf-8').read().split('REPO = ')[0])
from playwright.async_api import async_playwright

fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8796', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for zoom in (1.0, 1.15, 1.3, 1.45):
                ctx, pg, errs = await make_page(b, zoom=zoom)
                await pg.evaluate("openRoomDetail('r4')"); await pg.wait_for_timeout(2400)   # switcher runs every 900ms
                ok(await pg.evaluate("!!document.querySelector('#s-room-detail .detail-header #bp-kind-slot #bp-kind-switch')"), f'[{zoom}] Room/Area switch is not inside the header')
                ok(await pg.evaluate("!document.querySelector('#s-room-detail .detail-header ~ #bp-kind-switch')"), f'[{zoom}] old Counts-as row still below the header')
                ok(await pg.evaluate("document.querySelector('#bp-kind-switch').innerText.indexOf('Counts as')<0"), f'[{zoom}] "Counts as" label still showing')
                ok(await pg.evaluate("document.querySelectorAll('#bp-kind-switch button').length===2"), f'[{zoom}] expected Room + Area chips')
                # switch still works
                await pg.evaluate("document.querySelectorAll('#bp-kind-switch button')[1].click()"); await pg.wait_for_timeout(1300)
                ok(await pg.evaluate("DB.rooms.find(r=>r.id==='r4').kind==='location'"), f'[{zoom}] Area chip did not switch the kind')
                await pg.evaluate("document.querySelectorAll('#bp-kind-switch button')[0].click()"); await pg.wait_for_timeout(1300)
                ok(await pg.evaluate("DB.rooms.find(r=>r.id==='r4').kind==='room'"), f'[{zoom}] Room chip did not switch the kind')
                if zoom == 1.15: await pg.screenshot(path='/tmp/v348.png')
                # icon-only action row
                ok(await pg.evaluate("document.querySelectorAll('#s-room-detail .bp-act').length===3"), f'[{zoom}] expected 3 icon buttons')
                ok(await pg.evaluate("[...document.querySelectorAll('#s-room-detail .bp-act .bp-act-lb')].every(e=>getComputedStyle(e).display==='none')"), f'[{zoom}] labels should be hidden until tapped')
                # duplicates gone: the only Add Item / Add List controls are the three icon buttons
                ok(await pg.evaluate("document.querySelectorAll('#s-room-detail [onclick^=\"openAddNote(\"], #s-room-detail [onclick*=\";openAddNote(\"]').length===1"), f'[{zoom}] more than one Add Item control')
                ok(await pg.evaluate("document.querySelectorAll('#s-room-detail [onclick*=\"openBulkChecklist(\"]').length===1"), f'[{zoom}] more than one Add List control')
                ok(await pg.evaluate("!document.querySelector('#s-room-detail .section-header button[onclick*=\"openAddNote\"]')"), f'[{zoom}] Add Item still in the Checklist header')
                # tap shows the name
                await pg.evaluate("document.querySelectorAll('#s-room-detail .bp-act')[1].dispatchEvent(new MouseEvent('click',{bubbles:true}))"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("getComputedStyle(document.querySelectorAll('#s-room-detail .bp-act .bp-act-lb')[1]).display!=='none'"), f'[{zoom}] name did not appear on tap')
                await pg.evaluate("var m=document.getElementById('modal-bulk-checklist'); if(m) m.classList.remove('open')")
                await pg.wait_for_timeout(2700)
                ok(await pg.evaluate("getComputedStyle(document.querySelectorAll('#s-room-detail .bp-act .bp-act-lb')[1]).display==='none'"), f'[{zoom}] name did not tuck back in')
                # layout
                aud = await pg.evaluate("window.__audit('#s-room-detail')")
                ok(not aud.get('overflowX'), f"[{zoom}] horizontal overflow {aud.get('overflowX')}")
                ok(not aud.get('offscreen'), f"[{zoom}] offscreen {aud.get('offscreen')}")
                hdr_ov = [x for x in aud.get('overlap', []) if 'bp-kind' in x or 'bp-act' in x]
                ok(not hdr_ov, f'[{zoom}] overlaps {hdr_ov[:3]}')
                ok(not errs, f'[{zoom}] JS errors {errs[:2]}')
                await ctx.close()
            await b.close()
    finally: srv.terminate()
    print(f'\n{checks-len(fails)}/{checks} checks passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
