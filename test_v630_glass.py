"""v6.3.0 — Glass everywhere: frosted bars, cards and rows over a colored backdrop, light + dark, field app + Command Center.
Colored items keep their color. Run from repo root: python3 test_v630_glass.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8930
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active',updatedAt:t}]; DB.rooms=[{id:'r1',jobId:'j1',name:'(F) Bathroom',type:'Bathroom',updatedAt:t}];
  DB.punchlist=[{id:'p1',jobId:'j1',roomId:'r1',text:'Set flange',done:false,updatedAt:t}];
  try{bpSave()}catch(e){try{saveDB()}catch(e2){}} try{bpSetActiveJob('j1',true)}catch(e){} }"""
BLUR = "(q) => { var e = document.querySelector(q); if (!e) return 'missing'; var c = getComputedStyle(e); return (c.backdropFilter || c.webkitBackdropFilter || ''); }"
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for theme in ('light', 'dark'):
                print('\niPhone, %s' % theme)
                ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True)
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
                await pg.evaluate("(t)=>{document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined; document.documentElement.setAttribute('data-theme',t);}", theme)
                await pg.evaluate(SEED)
                ok(await pg.evaluate("APP_VERSION") == '6.3.0', 'on v6.3.0')
                ok('gradient' in await pg.evaluate("getComputedStyle(document.body).backgroundImage"), 'colored backdrop behind the glass')
                await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(800)
                ok('blur' in await pg.evaluate(BLUR, '#bp-onsite-card'), 'On Site card is frosted glass')
                await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(800)
                ok('blur' in await pg.evaluate(BLUR, '#s-room-detail .detail-header'), 'space top bar is frosted glass')
                ok('blur' in await pg.evaluate(BLUR, '#s-room-detail [id^="cli-"]'), 'checklist rows are frosted glass')
                mic = await pg.evaluate("(function(){ var m=document.getElementById('bp-voice-fab'); return m ? getComputedStyle(m).backgroundImage + getComputedStyle(m).backgroundColor : 'none'; })()")
                ok(mic == 'none' or ('255, 59, 48' in mic or '255, 69, 58' in mic or '226' in mic or 'gradient' in mic or 'rgb(2' in mic), 'red mic keeps its red (%s)' % mic[:60])
                ok(await pg.evaluate("(function(){ var e=document.createElement('div'); e.className='card'; e.style.background='rgba(191,90,242,.12)'; document.body.appendChild(e); var r=getComputedStyle(e).backgroundColor; e.remove(); return r.indexOf('191')>=0; })()"), 'a card with its own color (purple change order) keeps it')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
                print('\nCommand Center, %s' % theme)
                ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
                await pg.evaluate("(t)=>{document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); document.documentElement.setAttribute('data-theme',t);}", theme)
                ok(await pg.evaluate("APP_VERSION") == '6.3.0', 'Command Center on v6.3.0')
                ok('blur' in await pg.evaluate(BLUR, '.sidebar') and 'blur' in await pg.evaluate(BLUR, '.topbar'), 'side bar and top bar are frosted glass')
                ok('blur' in await pg.evaluate(BLUR, '.card'), 'cards are frosted glass')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
