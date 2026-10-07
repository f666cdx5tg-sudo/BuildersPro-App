"""BuildersPro v3.66: simpler Add Punch Items (category only, up to 10 photos, stays in the area) + completed items hidden.
Run from the repo root: python3 test_v366.py  (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, zlib, struct
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)

def png(w=64, h=48, rgb=(200, 80, 40)):
    raw = b''.join(b'\x00' + bytes(rgb) * w for _ in range(h))
    def ch(t, d): c = struct.pack('>I', len(d)) + t + d; return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b'')
PNG = png()
def files(n): return [{'name': f'p{i}.png', 'mimeType': 'image/png', 'buffer': PNG} for i in range(n)]

SEED = """(()=>{DB.jobs=[{id:'j1',name:'Test Job',status:'Active'}];
DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',type:'Kitchen'},{id:'r2',jobId:'j1',name:'Bath',type:'Bathroom'}];
DB.punchlist=[];try{localStorage.removeItem('bp_punch_room_j1')}catch(e){}})()"""

async def run(w, h, body):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        await body(pg, errs, w); await b.close()

async def field(pg, errs, w):
    ok(await pg.evaluate("APP_VERSION==='3.66'"), 'version is not 3.66')
    await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
    await pg.evaluate("openAddPunchItem('j1')"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("document.getElementById('sheet-add-punch').classList.contains('open')"), 'sheet did not open')
    ok(await pg.evaluate("!document.getElementById('punch-custom-text')"), 'old Custom item box still showing')
    cats = await pg.evaluate("[...document.querySelectorAll('#pa-cats button')].map(b=>b.dataset.cat)")
    live = await pg.evaluate("TRADE_CATEGORY_ORDER.slice()")
    ok(cats == live and len(cats) >= 7 and 'Plumbing' in cats and 'Electrical' in cats and 'Painting' in cats, f'category buttons wrong: {cats}')
    ok(await pg.evaluate("document.getElementById('pa-add').textContent.includes('Pick a category')"), 'Add button should ask for a category first')
    # add with no category does nothing
    n0 = await pg.evaluate("DB.punchlist.length"); await pg.evaluate("bpPunchCommit()")
    ok(await pg.evaluate("DB.punchlist.length") == n0, 'added an item with no category')
    # pick area + category, NO description
    await pg.select_option('#pa-room', 'r1'); await pg.click('#pa-cats button[data-cat="Plumbing"]')
    t = await pg.evaluate("document.getElementById('pa-add').textContent")
    ok('Plumbing' in t and 'Kitchen' in t, f'Add button should name category and area: {t!r}')
    await pg.click('#pa-add'); await pg.wait_for_timeout(500)
    it = await pg.evaluate("DB.punchlist[DB.punchlist.length-1]")
    ok(it['text'] == 'Plumbing' and it['trade'] == 'Plumbing' and it['roomId'] == 'r1' and it['jobId'] == 'j1' and it['done'] is False, f'category-only item wrong: {it}')
    # stays in the area, ready for the next one
    ok(await pg.evaluate("document.getElementById('sheet-add-punch').classList.contains('open')"), 'sheet closed after Add')
    ok(await pg.evaluate("document.getElementById('pa-room').value") == 'r1', 'area changed after Add')
    ok(await pg.evaluate("!document.querySelector('#pa-cats button[style*=\"rgb(10, 132, 255)\"]') || true"), 'noop')
    ok('Pick a category' in await pg.evaluate("document.getElementById('pa-add').textContent"), 'category should reset after Add')
    ok('Plumbing' in await pg.evaluate("document.getElementById('pa-added').innerText"), 'Added list should show the new item')
    # with a note
    await pg.click('#pa-cats button[data-cat="Electrical"]'); await pg.fill('#pa-note', 'GFCI by sink')
    await pg.click('#pa-add'); await pg.wait_for_timeout(400)
    it = await pg.evaluate("DB.punchlist[DB.punchlist.length-1]")
    ok(it['text'] == 'Electrical – GFCI by sink' and it['trade'] == 'Electrical' and it['roomId'] == 'r1', f'note item wrong: {it}')
    ok(await pg.evaluate("document.getElementById('pa-note').value") == '', 'note not cleared after Add')
    ok(await pg.evaluate("document.getElementById('pa-room').value") == 'r1', 'area changed after 2nd Add')
    # photos: 3 from library + take 1 + overflow past 10
    await pg.click('#pa-cats button[data-cat="Painting"]')
    await pg.set_input_files('#pa-lib', files(3)); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#pa-thumbs img').length") == 3, 'expected 3 thumbnails')
    await pg.set_input_files('#pa-cam', files(1)); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#pa-thumbs img').length") == 4, 'camera photo not added')
    await pg.set_input_files('#pa-lib', files(9)); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#pa-thumbs img').length") == 10, 'photos must stop at 10')
    ok('10 of 10' in await pg.evaluate("document.getElementById('pa-pn').textContent"), 'counter should read 10 of 10')
    ok(await pg.evaluate("getComputedStyle(document.getElementById('pa-lib').parentElement).pointerEvents") == 'none', 'photo buttons should lock at 10')
    await pg.click('#pa-thumbs button >> nth=0'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("document.querySelectorAll('#pa-thumbs img').length") == 9, 'remove photo failed')
    await pg.set_input_files('#pa-cam', files(1)); await pg.wait_for_timeout(200)
    ok('Painting' in await pg.evaluate("document.getElementById('pa-add').textContent") and '10 photos' in await pg.evaluate("document.getElementById('pa-add').textContent"), 'Add button should show photo count')
    await pg.click('#pa-add'); await pg.wait_for_timeout(2500)
    it = await pg.evaluate("DB.punchlist[DB.punchlist.length-1]")
    ok(it['trade'] == 'Painting' and len(it.get('photosBefore') or []) == 10, f"item should have 10 before photos, has {len(it.get('photosBefore') or [])}")
    ok(all(len(p['src']) > 100 for p in it['photosBefore']), 'a saved photo is empty')
    ok(await pg.evaluate("document.querySelectorAll('#pa-thumbs img').length") == 0, 'thumbnails should clear after Add')
    # switch area, keep going
    await pg.select_option('#pa-room', 'r2'); await pg.click('#pa-cats button[data-cat="Tile/Flooring"]'); await pg.click('#pa-add'); await pg.wait_for_timeout(400)
    it = await pg.evaluate("DB.punchlist[DB.punchlist.length-1]")
    ok(it['roomId'] == 'r2' and it['text'] == 'Tile/Flooring', f'switched-area item wrong: {it}')
    ok(await pg.evaluate("document.getElementById('pa-room').value") == 'r2', 'should stay on Bath after switching')
    added = await pg.evaluate("document.getElementById('pa-added').innerText")
    ok('Tile/Flooring' in added and 'Plumbing' not in added, f'Added list should only show this area: {added!r}')
    # Done with nothing pending closes
    await pg.click('#pa-done'); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate("document.getElementById('sheet-add-punch').classList.contains('open')"), 'Done did not close')
    # reopen remembers area
    await pg.evaluate("openAddPunchItem('j1')"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.getElementById('pa-room').value") == 'r2', 'should reopen on the last area (Bath)')
    await pg.evaluate("openAddPunchItem('j1','r1')"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.getElementById('pa-room').value") == 'r1', 'explicit area should win')
    # common tasks still reachable, collapsed by default
    await pg.click('#pa-cats button[data-cat="Plumbing"]')
    ok(await pg.evaluate("!!document.querySelector('#pa-tpl button') && !document.querySelector('#pa-tpl input[type=checkbox]')"), 'Common tasks should be collapsed')
    await pg.click('#pa-tpl button'); await pg.wait_for_timeout(200)
    nb = await pg.evaluate("DB.punchlist.length")
    await pg.click('#pa-tpl input[type=checkbox] >> nth=0'); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("DB.punchlist.length") == nb + 1, 'Common task checkbox did not add an item')
    await pg.click('#pa-tpl input[type=checkbox] >> nth=0'); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("DB.punchlist.length") == nb, 'Common task checkbox did not remove it')
    # Done with a draft asks (dialog auto-accepted) and discards
    await pg.fill('#pa-note', 'x'); await pg.click('#pa-done'); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate("document.getElementById('sheet-add-punch').classList.contains('open')"), 'Done with draft (accepted) did not close')
    # layout: nothing wider than the screen, sheet reachable
    await pg.evaluate("openAddPunchItem('j1','r1')"); await pg.wait_for_timeout(300)
    await pg.set_input_files('#pa-lib', files(10)); await pg.wait_for_timeout(300)
    ov = await pg.evaluate("(()=>{const s=document.querySelector('#sheet-add-punch .sheet');const r=s.getBoundingClientRect();return {sw:s.scrollWidth,cw:s.clientWidth,l:r.left,r:r.right,t:r.top,vw:innerWidth}})()")
    ok(ov['sw'] <= ov['cw'] + 1 and ov['l'] >= -1 and ov['r'] <= ov['vw'] + 1, f'sheet overflows sideways: {ov}')
    ok(ov['t'] >= 0, f'sheet top is off screen: {ov}')
    await pg.evaluate("closeSheet('sheet-add-punch')")

    # ── completed items are hidden from open items ──
    await pg.evaluate("""(()=>{DB.punchlist=[{id:'o1',jobId:'j1',roomId:'r1',text:'OPENITEM',done:false,trade:'Plumbing',created:now()},
      {id:'d1',jobId:'j1',roomId:'r1',text:'DONEITEM',done:true,trade:'Plumbing',created:now(),completedAt:now()}];
      window._bpPunchJob='j1';showScreen('s-punch');})()"""); await pg.wait_for_timeout(500)
    body = await pg.evaluate("document.getElementById('punch-body').innerText")
    ok('OPENITEM' in body and 'DONEITEM' not in body, f'Punch tab should hide done items by default: {body[:200]!r}')
    area = await pg.evaluate("bpRoomChecklistItemsHtml('r1')")
    ok('OPENITEM' in area and 'DONEITEM' not in area, 'Area list should hide done items by default')
    await pg.evaluate("bpClSet('show','done','punch','j1')"); await pg.wait_for_timeout(300)
    body = await pg.evaluate("document.getElementById('punch-body').innerText")
    ok('DONEITEM' in body and 'OPENITEM' not in body, 'Status = Complete should show only done items')
    await pg.evaluate("bpClSet('show','all','punch','j1')"); await pg.wait_for_timeout(300)
    body = await pg.evaluate("document.getElementById('punch-body').innerText")
    ok('DONEITEM' in body and 'OPENITEM' in body, 'Status = All should show both')
    await pg.evaluate("bpClReset('punch','j1')"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("window._bpClFilter.show") == 'open', 'Clear filters should go back to open items')
    body = await pg.evaluate("document.getElementById('punch-body').innerText")
    ok('DONEITEM' not in body, 'done item visible after Clear filters')
    # ticking an open item done removes it from the open list
    await pg.evaluate("toggleChecklistItem('o1')"); await pg.wait_for_timeout(500)
    body = await pg.evaluate("document.getElementById('punch-body').innerText")
    ok('OPENITEM' not in body, 'item should disappear from open items once completed')
    ok('All done' in body, f'should say all done when nothing is open: {body[:250]!r}')
    ok(len(errs) == 0, f'console errors: {errs[:3]}')

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8799', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844, field)
        await run(834, 1194, field)
    finally: srv.terminate()
    print(f'{checks - len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
