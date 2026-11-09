"""v6.9.19 — Slide Save · Move · Delete on every list (iPhone) + right-click / press-and-hold menu (Command Center),
and Assign photos (space, checklist item, Photos screen). Photos MOVE (one copy), never duplicate.
Run from repo root: python3 test_v6919_slide_assign.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8919
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.__posts=[];window.webkit={messageHandlers:{bp:{postMessage:function(m){window.__posts.push(m)}}}};"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
MKIMG = """(c) => { var k = document.createElement('canvas'); k.width = 60; k.height = 60; var g = k.getContext('2d'); g.fillStyle = c; g.fillRect(0,0,60,60); return k.toDataURL('image/jpeg', .8); }"""
SEED = """(I) => { var t = new Date().toISOString(), d = new Date(Date.now() - 864e5).toISOString();
 DB.jobs = [{ id:'j1', name:'Shedwick', client:'A', address:'1 St', status:'Active', updatedAt:t }, { id:'j2', name:'Elm Ave', client:'B', address:'2 St', status:'Active', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }, { id:'r2', jobId:'j1', name:'Bath', type:'Bathroom', updatedAt:t }, { id:'r3', jobId:'j2', name:'Porch', type:'Exterior', updatedAt:t }];
 DB.punchlist = [{ id:'p1', jobId:'j1', roomId:'r1', text:'Set vanity', done:false, photosBefore:[], photosAfter:[], updatedAt:t },
                 { id:'p2', jobId:'j1', roomId:'r1', text:'Caulk tub', done:false, photosBefore:[{ src:I[2], date:t }], photosAfter:[], updatedAt:t },
                 { id:'p3', jobId:'j1', roomId:'r2', text:'Hang mirror', done:false, photosBefore:[], photosAfter:[], updatedAt:t }];
 DB.photos = [{ id:'ph1', jobId:'j1', roomId:'', src:I[0], date:t, caption:'Niche' }, { id:'ph2', jobId:'j1', roomId:'', src:I[1], date:d },
              { id:'ph3', jobId:'j1', roomId:'r2', src:I[2], date:d }, { id:'ph4', jobId:'j2', roomId:'', src:I[3], date:d }];
 DB.documents = [{ id:'d1', jobId:'j1', name:'Signed contract', category:'Contract', fileSrc:I[0], fileName:'contract.jpg', fileType:'image/jpeg', created:t }];
 DB.expenses = [{ id:'e1', jobId:'j1', vendor:'Home Depot', amount:412.37, category:'Plumbing', date:t, receiptSrc:I[1] }];
 DB.invoices = [{ id:'i1', jobId:'j1', desc:'Deposit', amount:5000, status:'Sent', date:t }];
 DB.shopping = [{ id:'s1', jobId:'j1', name:'PEX elbows', qty:20, bought:false }];
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def setup(b, url, **kw):
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    imgs = [await pg.evaluate(MKIMG, c) for c in ('#c33', '#3c3', '#33c', '#cc3')]
    await pg.evaluate(SEED, imgs); await pg.evaluate("try { bpSetActiveJob('j1') } catch(e){}"); await pg.wait_for_timeout(300)
    return ctx, pg, errs
async def swipe(pg, cdp, el, dist=230):
    await el.evaluate("e => e.scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(250)
    bb = await el.bounding_box(); x, y = bb['x'] + bb['width'] * 0.75, bb['y'] + bb['height'] / 2
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
    for i in range(1, 11): await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x - dist * i / 10, 'y': y}]}); await pg.wait_for_timeout(16)
    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []}); await pg.wait_for_timeout(400)
async def pills(pg, scope):
    return await pg.evaluate("(s) => [].filter.call(document.querySelectorAll(s + ' .bp-pill'), function(b){ var r = b.getBoundingClientRect(); return r.width && r.right <= innerWidth + 1 && r.left >= -1; }).map(function(b){ return b.getAttribute('data-act'); })", scope)
async def tap(pg, sel):
    await pg.locator(sel).first.click()
async def pick_row(pg, text):
    await pg.locator('.bp6919-ov .bp6919-row', has_text=text).first.click(); await pg.wait_for_timeout(150)
async def phone(b):
    name = 'iPhone'; print('\n' + name)
    ctx, pg, errs = await setup(b, 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    cdp = await ctx.new_cdp_session(pg)
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 19), 'on v6.9.19 or newer')
    # ── checklist row
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    await swipe(pg, cdp, pg.locator('#s-room-detail .bp-cl-row[data-cl-id="p1"]'))
    P = await pills(pg, '#s-room-detail .bp-cl-row[data-cl-id="p1"]')
    ok(P == ['save', 'move', 'del'], 'checklist row slides to Save · Move · Delete, all on screen ' + str(P))
    cols = await pg.evaluate("[].map.call(document.querySelectorAll('#s-room-detail .bp-cl-row[data-cl-id=\"p1\"] .bp-pill-b'), function(e){ return getComputedStyle(e).backgroundColor; })")
    ok(cols == ['rgb(48, 209, 88)', 'rgb(255, 214, 10)', 'rgb(255, 69, 58)'], 'green / yellow / red ' + str(cols))
    await pg.screenshot(path='/tmp/claude-0/s/sl-check.png', clip={'x': 0, 'y': 300, 'width': 390, 'height': 300})
    await tap(pg, '#s-room-detail .bp-cl-row[data-cl-id="p1"] .bp-pill-save'); await pg.wait_for_timeout(200)
    sh = await pg.evaluate("window.__posts.filter(function(m){ return m.kind === 'share'; }).pop()")
    ok(sh and 'Set vanity' in sh['text'] and 'Kitchen' in sh['text'], 'Save → share sheet with the item ' + (sh and sh['text'][:40] or ''))
    await swipe(pg, cdp, pg.locator('#s-room-detail .bp-cl-row[data-cl-id="p1"]'))
    await tap(pg, '#s-room-detail .bp-cl-row[data-cl-id="p1"] .bp-pill-move'); await pg.wait_for_timeout(300)
    ok(await pg.is_visible('.bp6919-ov'), 'Move → picker')
    await pick_row(pg, 'Bath'); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate("DB.punchlist.find(function(p){ return p.id === 'p1'; }).roomId") == 'r2', 'item moved to Bath')
    await swipe(pg, cdp, pg.locator('#s-room-detail .bp-cl-row[data-cl-id="p2"]'))
    await tap(pg, '#s-room-detail .bp-cl-row[data-cl-id="p2"] .bp-pill-del'); await pg.wait_for_timeout(300)
    ok(await pg.is_visible('#bp-sw-confirm'), 'Delete asks first')
    await tap(pg, '#bp-sw-confirm .bp-sw-yes'); await pg.wait_for_timeout(600)
    ok(not await pg.evaluate("DB.punchlist.some(function(p){ return p.id === 'p2'; })"), 'Delete removes it')
    # ── assign photos to the space
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(600)
    ok(await pg.is_visible('#s-room-detail #bp6919-sp-asg .bp6919-asg'), 'space has + Assign photos')
    await tap(pg, '#s-room-detail #bp6919-sp-asg .bp6919-asg'); await pg.wait_for_timeout(400)
    n_unf = await pg.locator('.bp6919-ov .bp6919-g').count()
    ok(n_unf == 2, 'picker shows this job\'s Unfiled photos first (2) — %d' % n_unf)
    await tap(pg, '.bp6919-ov [data-k="tab"] button[data-v="all"]'); await pg.wait_for_timeout(150)
    ok(await pg.locator('.bp6919-ov .bp6919-g').count() == 3, 'All spaces adds the Bath photo (other jobs never shown)')
    await pg.screenshot(path='/tmp/claude-0/s/sl-assign.png')
    await pg.locator('.bp6919-ov .bp6919-g[data-p="ph1"]').click(); await pg.locator('.bp6919-ov .bp6919-g[data-p="ph3"]').click()
    ok('Assign 2 photos' in await pg.inner_text('.bp6919-ov .bp6919-go'), 'button counts the picks')
    await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
    rr = await pg.evaluate("DB.photos.map(function(p){ return p.id + ':' + p.roomId; }).join(' ')")
    ok('ph1:r1' in rr and 'ph3:r1' in rr and len(await pg.evaluate("DB.photos")) == 4, 'both MOVED to Kitchen (no copies) ' + rr)
    # ── item: Pick from job photos (via its photo sheet)
    await pg.evaluate("bpClPhotoSheet('p3')"); await pg.wait_for_timeout(300)
    ok(await pg.is_visible('#bp-clphoto-sheet .bp6919-pick'), 'item photo sheet has Pick from job photos')
    await tap(pg, '#bp-clphoto-sheet .bp6919-pick'); await pg.wait_for_timeout(300)
    await tap(pg, '.bp6919-ov [data-k="phase"] button[data-v="after"]')
    await pg.locator('.bp6919-ov .bp6919-g[data-p="ph2"]').click(); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
    it = await pg.evaluate("(function(){ var i = DB.punchlist.find(function(p){ return p.id === 'p3'; }); return [i.photosAfter.length, i.photosBefore.length]; })()")
    ok(it == [1, 0] and not await pg.evaluate("DB.photos.some(function(p){ return p.id === 'ph2'; })"), 'photo now an After photo on "Hang mirror", gone from Photos (moved) ' + str(it))
    # ── photos screen: Assign… and photo tile slide
    await pg.evaluate("showScreen('s-photos')"); await pg.wait_for_timeout(300)
    await pg.evaluate("window._bpPhotoArea = null; renderPhotos()"); await pg.wait_for_timeout(500)
    ok(await pg.is_visible('#bp6919-ph-asg .bp6919-asg'), 'Photos screen has Assign photos…')
    thumbs = await pg.evaluate("[].map.call(document.querySelectorAll('#s-photos .photo-thumb'), function(t){ return (t.getAttribute('onclick')||'').slice(0,30); })")
    tile = pg.locator('#s-photos .photo-thumb[onclick*="ph1"]')
    if await tile.count() == 0:
        await pg.evaluate("window._bpPhotoArea = 'r1'; renderPhotos()"); await pg.wait_for_timeout(500); tile = pg.locator('#s-photos .photo-thumb[onclick*="ph1"]')
    ok(await tile.count() == 1, 'photo tile found ' + str(thumbs[:3]))
    if await tile.count():
        await swipe(pg, cdp, tile, 90)
        P = await pills(pg, '#s-photos .photo-thumb[onclick*="ph1"] .bp6919-tov')
        ok(P == ['save', 'move', 'del'], 'photo tile slides open to Save · Move · Delete ' + str(P))
        await pg.screenshot(path='/tmp/claude-0/s/sl-photo.png', clip={'x': 0, 'y': 100, 'width': 390, 'height': 360})
        await tap(pg, '#s-photos .bp6919-tov .bp-pill-move'); await pg.wait_for_timeout(300)
        await pg.locator('.bp6919-ov .bp6919-row', has_text='Bath').first.click(); await pg.wait_for_timeout(150)   # tapping a space with items opens its items
        await pick_row(pg, 'Set vanity'); await tap(pg, '.bp6919-ov [data-k="phase"] button[data-v="before"]')
        await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
        # Set vanity was moved to Bath above — the picker lists it under Bath; accept either
        pv = await pg.evaluate("(DB.punchlist.find(function(p){ return p.id === 'p1'; }) || {}).photosBefore.length")
        ok(pv == 1 and not await pg.evaluate("DB.photos.some(function(p){ return p.id === 'ph1'; })"), 'Move a photo onto a checklist item (Before) — moved, not copied')
        ok(not await pg.evaluate("!!document.getElementById('viewer') && getComputedStyle(document.getElementById('viewer')).display !== 'none' && document.getElementById('viewer').classList.contains('open')"), 'sliding a photo never opens the viewer')
    # ── money tiles
    await pg.evaluate("showScreen('s-finance'); _financeTab = 'expenses'; renderFinance()"); await pg.wait_for_timeout(500)
    exp = pg.locator('#finance-content > div', has=pg.locator('button[onclick*="deleteFinItem"]')).first
    if await exp.count():
        await swipe(pg, cdp, exp)
        P = await pills(pg, '#finance-content .bp-sw-del')
        ok(P == ['save', 'move', 'del'], 'expense slides to Save · Move · Delete ' + str(P))
        await tap(pg, '#finance-content .bp-sw-del .bp-pill-save'); await pg.wait_for_timeout(200)
        sh = await pg.evaluate("window.__posts.filter(function(m){ return m.kind === 'share'; }).pop()")
        ok(sh and 'Home Depot' in sh['text'] and len(sh['files']) == 1, 'Save → expense text + receipt picture')
        await swipe(pg, cdp, exp); await tap(pg, '#finance-content .bp-sw-del .bp-pill-move'); await pg.wait_for_timeout(300)
        await pg.select_option('.bp6919-ov [data-k="job"]', 'j2'); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("DB.expenses[0].jobId") == 'j2', 'Move → expense now on Elm Ave')
    await pg.evaluate("_financeTab = 'invoices'; renderFinance()"); await pg.wait_for_timeout(500)
    inv = pg.locator('#finance-content > div', has=pg.locator('button[onclick*="deleteFinItem"]')).first
    if await inv.count():
        await swipe(pg, cdp, inv)
        P = await pills(pg, '#finance-content .bp-sw-del')
        ok(P == ['save', 'del'], 'invoice slides to Save · Delete (no Move) ' + str(P))
        await tap(pg, '#finance-content .bp-sw-del .bp-pill-save'); await pg.wait_for_timeout(200)
        sh = await pg.evaluate("window.__posts.filter(function(m){ return m.kind === 'share'; }).pop()")
        ok(sh and 'Deposit' in sh['text'] and '$5,000.00' in sh['text'], 'invoice Save text ' + (sh and sh['text'][:60] or ''))
    # ── documents (job page)
    await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(700)
    await pg.evaluate("try { if (typeof renderDocumentsSection === 'function') renderDocumentsSection('j1'); } catch(e){}"); await pg.wait_for_timeout(300)
    drow = pg.locator('.bp-doc-swipe > .bp-doc-row').first
    if await drow.count():
        await drow.scroll_into_view_if_needed(); await swipe(pg, cdp, drow)
        P = await pills(pg, '.bp-doc-swipe .bp-doc-acts')
        ok(P == ['save', 'move', 'del'], 'document slides to Save · Move · Delete ' + str(P))
        await tap(pg, '.bp-doc-swipe .bp-pill-move'); await pg.wait_for_timeout(300)
        await pg.select_option('.bp6919-ov [data-k="cat"]', 'Permit'); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("DB.documents[0].category") == 'Permit', 'Move → document category changed')
    else:
        ok(False, 'documents row not found on job page')
    # ── shopping
    await pg.evaluate("bpOpenShop()"); await pg.wait_for_timeout(600)
    srow = pg.locator('[data-shop-id="s1"]')
    if await srow.count():
        await swipe(pg, cdp, srow)
        P = await pills(pg, '[data-shop-id="s1"] .bp-sw-del')
        ok(P == ['move', 'del'], 'shopping item slides to Move · Delete ' + str(P))
    else: ok(False, 'shopping row not found')
    ok(not errs, 'no script errors ' + str(errs[:3]))
    await ctx.close()
async def cc(b, name, **kw):
    print('\n' + name)
    ctx, pg, errs = await setup(b, 'desktop.html', **kw)
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    ok(await pg.is_visible('#modal-room-detail #bp6919-sp-asg .bp6919-asg'), name + ': space has + Assign photos')
    row = pg.locator('#bp-desk-checklist > div', has_text='Set vanity').first
    await row.click(button='right'); await pg.wait_for_timeout(250)
    P = await pills(pg, '#bp6919-menu')
    ok(P == ['save', 'move', 'del'], name + ': right-click a checklist item → Save · Move · Delete ' + str(P))
    ok(await pg.is_visible('#bp6919-menu .bp6919-extra'), name + ': …and Assign photos')
    await pg.screenshot(path='/tmp/claude-0/s/sl-%s.png' % name.split()[0])
    await tap(pg, '#bp6919-menu .bp-pill-move'); await pg.wait_for_timeout(300)
    await pick_row(pg, 'Bath'); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate("DB.punchlist.find(function(p){ return p.id === 'p1'; }).roomId") == 'r2', name + ': Move works')
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
    await tap(pg, '#modal-room-detail #bp6919-sp-asg .bp6919-asg'); await pg.wait_for_timeout(300)
    await pg.locator('.bp6919-ov .bp6919-g[data-p="ph1"]').click(); await tap(pg, '.bp6919-ov .bp6919-go'); await pg.wait_for_timeout(500)
    ok(await pg.evaluate("DB.photos.find(function(p){ return p.id === 'ph1'; }).roomId") == 'r1', name + ': Assign photos to the space')
    ok(not errs, name + ': no script errors ' + str(errs[:3]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await phone(b)
            await cc(b, 'iPad Command Center', viewport={'width': 1180, 'height': 820}, user_agent=IPAD, has_touch=True)
            await cc(b, 'Mac Command Center', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
