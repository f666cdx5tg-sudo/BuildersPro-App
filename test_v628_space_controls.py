"""v6.2.8 — Space checklist: Open / Complete / Select not cramped, and answer one tap (with a little thumb drift).
Run from repo root: python3 test_v628_space_controls.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8928
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',client:'A',address:'1 St',status:'Active',updatedAt:t}];
  DB.rooms=[{id:'r1',jobId:'j1',name:'(F) Bathroom',type:'Bathroom',level:'Level 1',updatedAt:t}];
  DB.punchlist=[]; for (var i=1;i<=12;i++) DB.punchlist.push({id:'p'+i,jobId:'j1',roomId:'r1',text:'ITEM-'+i,done:true,status:'Done',completedAt:t,updatedAt:t});
  try{bpSave()}catch(e){} try{bpSetActiveJob('j1',true)}catch(e){} }"""

async def run(b, zoom):
    print('\niPhone, text size %s' % zoom)
    ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True, device_scale_factor=2)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("(z) => { document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined; localStorage.setItem('bp_zoom', z); try { bpApplyZoom(); } catch(e){} }", str(zoom))
    await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(800)
    await pg.evaluate("document.querySelector('#s-room-detail .bp-seg').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("APP_VERSION") >= '6.2.8', 'on v6.2.8')
    fit = await pg.evaluate("[].map.call(document.querySelectorAll('#s-room-detail .bp-seg button'), function(b){ return b.scrollWidth <= b.clientWidth + 1; })")
    fw = await pg.evaluate("[].map.call(document.querySelectorAll('#s-room-detail .bp-seg button'), function(b){ return [b.scrollWidth, b.clientWidth]; })"); ok(fit == [True, True], str(fw) + ' ' + '"Open 0" and "Complete 12" fit inside their buttons')
    sel = await pg.evaluate("(function(){ var b=document.querySelector('#s-room-detail .bp-selbtn'), s=document.querySelector('#s-room-detail .bp-seg'); var r=b.getBoundingClientRect(), q=s.getBoundingClientRect(); return [Math.round(r.width/ (parseFloat(getComputedStyle(document.body).zoom)||1)), b.getAttribute('aria-label'), q.right <= r.left, !!b.querySelector('svg')]; })()")
    ok(sel[0] <= 48 and sel[1] == 'Select' and sel[2] and sel[3], 'Select is a square line-icon button beside Open/Complete, no overlap %s' % sel)
    await pg.evaluate("window.__n=0; var o=window.bpSpaceShow; window.bpSpaceShow=function(){ window.__n++; return o.apply(this, arguments); }; window.__s=0; var p=window.bpOpenSelect; window.__st=[]; window.bpOpenSelect=function(){ window.__s++; window.__st.push(new Error().stack.split(String.fromCharCode(10)).slice(1,4).join(' | ')); }; 0")
    cdp = await ctx.new_cdp_session(pg)
    async def tap(q, dx, dy):
        x, y = await pg.evaluate("(q) => { var b=document.querySelector(q).getBoundingClientRect(); return [b.left+b.width/2, b.top+b.height/2]; }", q)
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
        for i in range(1, 5): await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + dx * i / 4, 'y': y + dy * i / 4}]})
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        await pg.wait_for_timeout(500)
    await tap('#s-room-detail .bp-seg button[data-bp-show=done]', 0, 0)
    ok(await pg.evaluate("[window.__n, window._bpClFilter.show]") == [1, 'done'], 'a clean tap on Complete works once')
    vis = await pg.evaluate("[].filter.call(document.querySelectorAll('#s-room-detail .bp-cl-name, #s-room-detail [id^=cli-]'), function(e){ return e.offsetParent; }).length")
    ok(vis >= 12, 'the 12 done items show (%d)' % vis)
    await tap('#s-room-detail .bp-seg button[data-bp-show=open]', 14, 6)
    ok(await pg.evaluate("[window.__n, window._bpClFilter.show]") == [2, 'open'], 'a thumb tap that drifts 14px still switches to Open')
    await tap('#s-room-detail .bp-seg button[data-bp-show=done]', -12, 9)
    ok(await pg.evaluate("window._bpClFilter.show") == 'done', 'drifting the other way still works')
    await tap('#s-room-detail .bp-selbtn', 12, 4)
    s1 = await pg.evaluate("window.__s"); ok(s1 == 1, 'Select answers a drifting tap, once (%s)' % s1)
    await tap('#s-room-detail .bp-selbtn', 0, 60)
    ok(await pg.evaluate("window.__s") == 1, 'a scroll that starts on Select does not press it')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def mac(b):
    print('\nCommand Center')
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
    ok(await pg.evaluate("APP_VERSION") >= '6.2.8', 'Command Center is v6.2.8')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for z in (1.15, 1.3, 1.45): await run(b, z)
            await mac(b); await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
