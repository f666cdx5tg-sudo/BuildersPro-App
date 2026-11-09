"""v6.9.18 — Room scan: + Scan in every space saves straight into that space (iPhone field app AND iPad
Command Center — the iPad used to drop the scan); each space shows its scans; tapping one opens a viewer with
zoom (pinch / scroll), move, rotate (twist / Rotate button), Fit, and View in 3D. Scans opened from Photos use it.
Run from repo root: python3 test_v6918_room_scan.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8918
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
def shell(scan=True, v3d=True):
    on = 'true' if scan else 'false'
    return ("window.BPShell={version:'t',caps:{ai:true,measure:%s,lidar:%s,roomScan:%s,roomView3D:%s}};window.__posts=[];"
            "window.webkit={messageHandlers:{bp:{postMessage:function(m){window.__posts.push(m)}}}};") % (on, on, on, 'true' if v3d else 'false')
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
# a 400x300 plan image
IMG = None
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'Shedwick', client:'A', address:'1 St', status:'Active', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }, { id:'r2', jobId:'j1', name:'Bath', type:'Bathroom', updatedAt:t }];
 DB.punchlist = []; DB.photos = [];
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
MKIMG = """() => { var c = document.createElement('canvas'); c.width = 400; c.height = 300; var g = c.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0,0,400,300); g.strokeStyle = '#000'; g.lineWidth = 6; g.strokeRect(40,40,320,220); return c.toDataURL('image/jpeg', .8); }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
def result(img, usdz='Room scan 2026-11-09 10.00.usdz'):
    return {'tool':'room','ok':True,'image':img,'areaSqFt':132.4,'ceiling':"8' 1\"",'perimeter':"46' 3\"",'perimeterFt':46.25,
            'wallCount':4,'doors':1,'windows':2,'walls':["12' 0\"","11' 1\"","12' 0\"","11' 1\""],'usdz':usdz}
async def run(b, name, url, **kw):
    print('\n' + name)
    mac = 'desktop' in url
    ctx = await b.new_context(**kw); await ctx.add_init_script(shell())
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 18), name + ': on v6.9.18 or newer')
    img = await pg.evaluate(MKIMG)
    await pg.evaluate(SEED); await pg.evaluate("try { bpSetActiveJob('j1') } catch(e){}")
    host = '#modal-room-detail' if mac else '#s-room-detail'
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    ok(await pg.is_visible(host + ' #bp-scan-sec'), name + ': space has a ROOM SCAN section')
    ok(await pg.is_visible(host + ' .bp-sc-add'), name + ': + Scan button (LiDAR device)')
    await pg.click(host + ' .bp-sc-add'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("window.__posts.some(function(m){ return m.kind === 'roomScan'; })"), name + ': Scan asks the app for a room scan')
    # the user wanders off to another space while scanning, then the scan comes back
    await pg.evaluate("openRoomDetail('r2')"); await pg.wait_for_timeout(300)
    await pg.evaluate("r => bpNativeDone(r)", result(img)); await pg.wait_for_timeout(800)
    ph = await pg.evaluate("DB.photos.map(function(p){ return [p.roomId, p.jobId, !!p.scan, p.scan && p.scan.usdz]; })")
    ok(len(ph) == 1 and ph[0][:3] == ['r1', 'j1', True], name + ': scan saved straight into the space it was started from (Kitchen) ' + str(ph))
    ok(not await pg.evaluate("!!document.getElementById('bp-tool-save')"), name + ': no extra questions')
    ok(await pg.evaluate("(document.querySelector('%s') || {getAttribute:function(){}}).getAttribute('data-room-id')" % host) == 'r1', name + ': Kitchen is open again, showing the scan')
    await pg.wait_for_timeout(300)
    rows = await pg.locator(host + ' .bp-sc-row').count()
    txt = await pg.inner_text(host + ' #bp-scan-sec')
    ok(rows == 1 and '132.4 sq ft' in txt and "ceiling 8' 1\"" in txt and '4 walls' in txt and '1 door ·' in txt, name + ': scan card shows area, ceiling, walls ' + repr(txt[:90]))
    await pg.screenshot(path='/tmp/claude-0/s/scan-%s-space.png' % name.split()[0])
    # viewer
    await pg.click(host + ' .bp-sc-row'); await pg.wait_for_timeout(500)
    ok(await pg.is_visible('#bp-scanv'), name + ': tapping the scan opens it')
    T = lambda: pg.evaluate("JSON.parse(JSON.stringify(window.__bpScanT))")
    t0 = await T()
    box = await pg.locator('#bp-scanv .bp-sv-stage').bounding_box(); cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    # two-finger pinch out + twist (pointer events)
    await pg.evaluate("""([cx,cy]) => { var st = document.querySelector('#bp-scanv .bp-sv-stage');
      function ev(t, id, x, y){ st.dispatchEvent(new PointerEvent(t, { pointerId:id, clientX:x, clientY:y, bubbles:true, pointerType:'touch' })); }
      st.setPointerCapture = function(){};
      ev('pointerdown', 1, cx-50, cy); ev('pointerdown', 2, cx+50, cy);
      ev('pointermove', 1, cx-100, cy-30); ev('pointermove', 2, cx+100, cy+30);
      ev('pointerup', 1, cx-100, cy-30); ev('pointerup', 2, cx+100, cy+30); }""", [cx, cy])
    t1 = await T()
    ok(t1['s'] > 1.9, name + ': pinch zooms in (%.2fx)' % t1['s'])
    ok(abs(t1['r']) > 10, name + ': two-finger twist rotates (%.1f°)' % t1['r'])
    await pg.mouse.move(cx, cy); await pg.mouse.wheel(0, -300); await pg.wait_for_timeout(100)
    ok((await T())['s'] > t1['s'], name + ': scroll wheel zooms (Mac / iPad trackpad)')
    await pg.click('#bp-scanv button[data-a="fit"]'); await pg.wait_for_timeout(100); t2 = await T()
    ok(t2['s'] == 1 and t2['r'] == 0 and t2['x'] == 0, name + ': Fit puts it back')
    await pg.click('#bp-scanv button[data-a="rot"]'); await pg.wait_for_timeout(100)
    ok((await T())['r'] == 90, name + ': Rotate turns it 90°')
    await pg.mouse.move(cx, cy); await pg.mouse.down(); await pg.mouse.move(cx + 80, cy + 40, steps=4); await pg.mouse.up()
    t3 = await T(); ok(t3['x'] > 50 and t3['y'] > 20, name + ': drag moves it')
    ok("12' 0\"" in await pg.inner_text('#bp-scanv .bp-sv-facts'), name + ': each wall length listed')
    await pg.screenshot(path='/tmp/claude-0/s/scan-%s-viewer.png' % name.split()[0])
    await pg.evaluate("window.__posts = []"); await pg.click('#bp-scanv .bp-sv-3d'); await pg.wait_for_timeout(100)
    P = await pg.evaluate("window.__posts"); ok({'kind': 'roomView3D', 'name': 'Room scan 2026-11-09 10.00.usdz'} in P, name + ': View in 3D opens the 3D model ' + json.dumps(P)[:160])
    await pg.click('#bp-scanv button[data-a="close"]'); await pg.wait_for_timeout(200)
    ok(not await pg.evaluate("!!document.getElementById('bp-scanv')"), name + ': close')
    pid = await pg.evaluate("DB.photos[0].id")
    await pg.evaluate("viewPhoto('%s')" % pid); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("!!document.getElementById('bp-scanv')"), name + ': opening the scan from Photos opens the scan viewer')
    await pg.evaluate("document.getElementById('bp-scanv').remove()")
    # scan started from the menu (no space) — field app still asks; Command Center saves to the job, never drops it
    await pg.evaluate("r => bpNativeDone(r)", result(img, '')); await pg.wait_for_timeout(500)
    if mac:
        ok(await pg.evaluate("DB.photos.length") == 2 and await pg.evaluate("DB.photos[1].jobId") == 'j1', name + ': a scan with no space is saved to the job, not dropped')
    else:
        ok(await pg.evaluate("!!document.getElementById('bp-tool-save')"), name + ': a scan from the menu still asks job / area')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def nolidar(b):
    print('\nNo LiDAR (plain iPhone)')
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    await ctx.add_init_script(shell(False, False)); pg = await ctx.new_page()
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(4000)
    await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(600)
    ok(not await pg.is_visible('#s-room-detail .bp-sc-add'), 'no Scan button where it can\'t work')
    ok(not await pg.evaluate("(document.getElementById('bp-scan-sec') || {}).innerText"), 'no empty section taking room')
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'iPad Command Center', 'desktop.html', viewport={'width': 1180, 'height': 820}, user_agent=IPAD, has_touch=True)
            await nolidar(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
