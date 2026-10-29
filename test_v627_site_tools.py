"""v6.2.7 — Measure + Room scan (native app) and pipe slope on the Level.
1. In a plain browser the Measure / Room scan buttons stay hidden (they need the App Store app).
2. Inside the app (simulated shell): buttons show, tapping asks the app, results save to the On Site job + area.
3. Level: pick 1/4" per ft; on grade turns green, short of it says "Needs more fall".
4. Command Center loads on the same version.
Run from repo root: python3 test_v627_site_tools.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8927
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
SEED = """() => {
  var t = new Date().toISOString();
  DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', updatedAt:t },
             { id:'j2', name:'Other Job', client:'B', address:'2 St', status:'Active', updatedAt:t }];
  DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', level:'Level 1', updatedAt:t },
              { id:'r2', jobId:'j2', name:'Garage', type:'Other', level:'Level 1', updatedAt:t }];
  DB.photos = [];
  try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} }
  try { bpSetActiveJob('j1', true); } catch(e){}
}"""
SHELL = """
window.__posts = [];
window.webkit = { messageHandlers: { bp: { postMessage: function(m){ window.__posts.push(m); } } } };
window.BPShell = { version: 'test', caps: { measure: true, lidar: true, roomScan: true } };
"""

async def open_field(b, shell):
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    if shell: await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    return ctx, pg, errs

async def field(b):
    print('\nBrowser (no app)')
    ctx, pg, errs = await open_field(b, False)
    ok(await pg.evaluate("APP_VERSION") >= '6.2.7', 'field app is v6.2.7')
    ok(await pg.evaluate("getComputedStyle(document.getElementById('nav-measure')).display") == 'none', 'Measure hidden in a plain browser')
    ok(await pg.evaluate("getComputedStyle(document.getElementById('nav-roomscan')).display") == 'none', 'Room scan hidden in a plain browser')

    print('\nLevel — pipe slope')
    await pg.evaluate(SEED)
    await pg.evaluate("DeviceOrientationEvent.requestPermission = function(){ return Promise.resolve('granted'); }; bpLevelOpen()"); await pg.wait_for_timeout(300)
    async def tilt(g):
        await pg.evaluate("""(g) => { for (var i = 0; i < 60; i++) window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', { alpha: 0, beta: g, gamma: 90 })); }""", g)
        await pg.wait_for_timeout(250)
    await tilt(0.0)
    ok(await pg.evaluate("document.querySelectorAll('.bp-lv-chip').length") == 4, 'Level on its edge shows 4 slope choices (Level, 1/8, 1/4, 1/2)')
    await pg.evaluate("bpLevelSlope('0.25')"); await pg.wait_for_timeout(100)
    ok(await pg.evaluate("document.querySelector('.bp-lv-chip.on').getAttribute('data-slope')") == '0.25', '1/4" per ft picked')
    await tilt(1.19)   # phone on its long edge along the pipe; atan(0.25/12) = 1.19 degrees
    sub = await pg.inner_text('#bp-lv-sub'); green = await pg.evaluate("document.getElementById('bp-lv-stage').classList.contains('bp-lv-ok')")
    ok('ON GRADE' in sub and green, 'pipe at 1/4" per ft reads ON GRADE in green (%s)' % sub)
    await tilt(0.5)
    sub = await pg.inner_text('#bp-lv-sub'); green = await pg.evaluate("document.getElementById('bp-lv-stage').classList.contains('bp-lv-ok')")
    ok('Needs more fall' in sub and not green, 'pipe short of 1/4" says Needs more fall (%s)' % sub)
    await tilt(3.0)
    ok('Too steep' in await pg.inner_text('#bp-lv-sub'), 'too much fall says Too steep')
    await pg.evaluate("bpLevelSlope('')"); await tilt(0.0)
    ok('LEVEL' in await pg.inner_text('#bp-lv-sub'), 'back to plain Level reads LEVEL')
    await pg.evaluate("bpLevelClose()")
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

    print('\nInside the app (simulated)')
    ctx, pg, errs = await open_field(b, True)
    await pg.evaluate(SEED)
    ok(await pg.evaluate("getComputedStyle(document.getElementById('nav-measure')).display") != 'none', 'Measure shows in the app')
    ok(await pg.evaluate("getComputedStyle(document.getElementById('nav-roomscan')).display") != 'none', 'Room scan shows in the app')
    n_line = await pg.evaluate("document.querySelectorAll('#nav-measure svg, #nav-roomscan svg').length")
    ok(n_line == 2, 'both buttons use line icons')
    await pg.evaluate("bpMeasureOpen(); bpRoomScanOpen()")
    kinds = await pg.evaluate("__posts.map(function(m){ return m.kind; }).filter(function(k){ return k.indexOf('ai') !== 0; })")
    ok(kinds == ['measure', 'roomScan'], 'buttons ask the app for Measure and Room scan %s' % kinds)

    await pg.evaluate("bpNativeDone({ tool:'measure', ok:false, cancel:true })")
    ok(not await pg.evaluate("!!document.getElementById('bp-tool-save')"), 'closing Measure saves nothing')

    await pg.evaluate("(src) => bpNativeDone({ tool:'measure', ok:true, image: src, lengths:['3\\' 4 1/2\"'], inches:[40.5], lidar:true })", PNG)
    ok(await pg.evaluate("!!document.getElementById('bp-tool-save')"), 'a measurement opens the save sheet')
    ok(await pg.evaluate("document.getElementById('bp-ts-job').value") == 'j1', 'save sheet defaults to the On Site job')
    rooms = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-ts-room option'), function(o){ return o.textContent; })")
    ok(rooms == ['No area', 'Kitchen'], 'area list only has this job\'s areas %s' % rooms)
    await pg.select_option('#bp-ts-room', 'r1')
    await pg.click('#bp-ts-save'); await pg.wait_for_timeout(300)
    p = await pg.evaluate("DB.photos[DB.photos.length-1]")
    ok(p and p['jobId'] == 'j1' and p['roomId'] == 'r1', 'measurement saved to the job and Kitchen')
    ok(p and '3\' 4 1/2"' in p['caption'] and p['tags'] == ['Measure'], 'caption carries the length (%s)' % (p and p['caption']))
    ok(p and p['measure']['inches'] == [40.5], 'raw inches kept for estimating')

    await pg.evaluate("(src) => bpNativeDone({ tool:'room', ok:true, image: src, walls:['12\\' 0\"','10\\' 6\"'], wallCount:4, doors:1, windows:2, openings:0, areaSqFt:126.4, perimeter:'45\\' 0\"', perimeterFt:45, ceiling:'8\\' 1\"', usdz:'Room scan 2026-10-28 21.40.usdz' })", PNG)
    txt = await pg.inner_text('#bp-tool-save')
    ok('126.4 sq ft' in txt and "8' 1\"" in txt and '4 walls' in txt, 'room scan sheet shows area, ceiling, walls')
    await pg.evaluate("__posts = []"); await pg.click('#bp-tool-save button[onclick^="bpShare3D"]')
    ok(await pg.evaluate("__posts.length && __posts[0].kind === 'roomShare3D' && __posts[0].name.indexOf('.usdz') > 0"), 'Share 3D model asks the app for the USDZ file')
    await pg.select_option('#bp-ts-job', 'j2'); await pg.wait_for_timeout(100)
    rooms = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-ts-room option'), function(o){ return o.textContent; })")
    ok(rooms == ['No area', 'Garage'], 'switching job switches the area list %s' % rooms)
    await pg.select_option('#bp-ts-job', 'j1')
    await pg.click('#bp-ts-save'); await pg.wait_for_timeout(300)
    p = await pg.evaluate("DB.photos[DB.photos.length-1]")
    ok(p and p['tags'] == ['Room scan'] and p['scan']['areaSqFt'] == 126.4 and p['jobId'] == 'j1', 'room scan saved with its numbers')
    ok(await pg.evaluate("DB.photos.length") == 2, 'two photos on the job')
    ok(await pg.evaluate("!document.getElementById('bp-tool-save')"), 'sheet closes after saving')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def mac(b):
    print('\nCommand Center')
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
    ok(await pg.evaluate("APP_VERSION") >= '6.2.7', 'Command Center is v6.2.7')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await field(b); await mac(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
