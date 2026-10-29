"""v6.2.9 — Level details: fraction per ft, degrees + % grade, total drop over a run, vial marks, Hold, Save to job.
Run from repo root: python3 test_v629_level.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8929
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True)
            await ctx.add_init_script("window.__posts=[]; window.webkit={messageHandlers:{bp:{postMessage:function(m){window.__posts.push(m)}}}};")
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("""() => { document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;
              var t = new Date().toISOString(); DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active',updatedAt:t}]; DB.rooms=[{id:'r1',jobId:'j1',name:'(F) Bathroom',type:'Bathroom',updatedAt:t}]; DB.photos=[];
              try{bpSave()}catch(e){} try{bpSetActiveJob('j1',true)}catch(e){}
              localStorage.setItem('bp_lvl_cal','{}'); localStorage.setItem('bp_lvl_target','0.25'); localStorage.setItem('bp_lvl_run','12');
              DeviceOrientationEvent.requestPermission=function(){return Promise.resolve('granted')}; bpLevelOpen(); }""")
            ok(await pg.evaluate("APP_VERSION") >= '6.2.9', 'on v6.2.9')
            async def tilt(beta, gamma=90):
                await pg.evaluate("(a) => { for (var i=0;i<60;i++) window.dispatchEvent(new DeviceOrientationEvent('deviceorientation',{alpha:0,beta:a[0],gamma:a[1]})); }", [beta, gamma]); await pg.wait_for_timeout(300)
            await tilt(1.0)
            ok(await pg.inner_text('#bp-lv-num') == '3/16"', 'big reading is a fraction per ft (3/16")')
            meta = await pg.inner_text('#bp-lv-meta')
            ok('1.0°' in meta and '1.75%' in meta, 'degrees and %% grade shown (%s)' % meta)
            drop = await pg.inner_text('#bp-lv-drop')
            ok('2 1/2"' in drop and 'need 3"' in drop and '1/2" short' in drop, 'total drop over 12 ft with how far off (%s)' % drop)
            ok(await pg.evaluate("document.querySelectorAll('#bp-lv-vial .bp-lv-tk').length") == 16, 'vial has tick marks every 1/8" per ft')
            ok(await pg.evaluate("getComputedStyle(document.getElementById('bp-lv-tg1')).display") == 'block', 'blue marks show the picked grade on the vial')
            await pg.evaluate("__posts=[]"); await tilt(1.19)
            ok('ON GRADE' in await pg.inner_text('#bp-lv-sub') and 'on' in await pg.inner_text('#bp-lv-drop'), 'on grade reads ON GRADE and drop "on"')
            ok(await pg.evaluate("__posts.some(function(m){ return m.kind === 'haptic'; })"), 'phone buzzes when it hits grade')
            await pg.evaluate("bpLevelSlope('')"); await tilt(0.05)
            ok('LEVEL' in await pg.inner_text('#bp-lv-sub'), 'plain level within 0.1° reads LEVEL')
            await tilt(0.3)
            ok('LEVEL' not in await pg.inner_text('#bp-lv-sub'), '0.3° is no longer called level (tighter than before)')
            await pg.evaluate("bpLevelHold()"); held = await pg.inner_text('#bp-lv-num'); await tilt(3)
            ok(await pg.inner_text('#bp-lv-num') == held and await pg.inner_text('#bp-lv-hold') == 'Held', 'Hold freezes the reading')
            await pg.evaluate("bpLevelHold()"); await tilt(3)
            ok(await pg.inner_text('#bp-lv-num') != held, 'tap again to let it go')
            await pg.evaluate("(b64) => { var bin = atob(b64), u = new Uint8Array(bin.length); for (var i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i); window.__f = new File([u], 'x.png', {type:'image/png'}); var oc = HTMLInputElement.prototype.click; HTMLInputElement.prototype.click = function(){ if (this.type === 'file') { var dt = new DataTransfer(); dt.items.add(window.__f); this.files = dt.files; this.onchange(); return; } return oc.apply(this, arguments); }; }", PNG)
            await pg.evaluate("bpLevelSave()"); await pg.wait_for_timeout(800)
            ok(await pg.evaluate("!!document.getElementById('bp-tool-save')"), 'Save takes a photo and opens the save sheet')
            ok('Level reading' in await pg.inner_text('#bp-tool-save'), 'sheet is titled Level reading')
            await pg.click('#bp-ts-save'); await pg.wait_for_timeout(300)
            ph = await pg.evaluate("DB.photos[DB.photos.length-1]")
            ok(ph and ph['tags'] == ['Level'] and ph['jobId'] == 'j1' and ph['level']['inPerFt'] > 0, 'reading saved to the job as a photo with its numbers')
            ok(not errs, 'no page errors %s' % errs[:2])
            await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
