"""BuildersPro v4.53 (Level + Color match tools in the drawer).
Run from repo root: python3 test_v446.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, math
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
ORI = "(([b,g])=>window.dispatchEvent(new DeviceOrientationEvent('deviceorientation',{beta:b,gamma:g,alpha:0,absolute:false})))"
async def tilt(pg, b, g):
    for _ in range(40): await pg.evaluate(ORI + "([%s,%s])" % (b, g)); await pg.wait_for_timeout(8)
    await pg.wait_for_timeout(120)
async def run(w, h, theme):
    async with async_playwright() as p:
        br = await p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
        ctx = await br.new_context(viewport={'width': w, 'height': h}, permissions=['camera'])
        pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8794/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.53'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        # drawer buttons
        ok(await pg.evaluate("!!document.getElementById('nav-level')&&!!document.getElementById('nav-colormatch')"), f'{t}: drawer buttons')
        # ---------- LEVEL ----------
        await pg.evaluate("document.getElementById('nav-level').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!!document.getElementById('bp-level')"), f'{t}: level opens')
        await tilt(pg, 0, 0)
        ok(await pg.evaluate("document.getElementById('bp-lv-num').textContent")=='0.0°', f'{t}: flat level reading')
        ok('LEVEL' in await pg.evaluate("document.getElementById('bp-lv-sub').textContent"), f'{t}: LEVEL label')
        ok(await pg.evaluate("document.getElementById('bp-lv-stage').classList.contains('bp-lv-ok')"), f'{t}: ok state')
        col = await pg.evaluate("getComputedStyle(document.getElementById('bp-lv-bub')).borderTopColor")
        ok(col=='rgb(48, 209, 88)', f'{t}: bubble green when level {col}')
        # right edge down 4 degrees -> 4.0, bubble moves LEFT (away from low side), says Right side low
        await tilt(pg, 0, 4)
        ok(await pg.evaluate("document.getElementById('bp-lv-num').textContent")=='4.0°', f'{t}: 4 deg reading')
        ok('Right side low' in await pg.evaluate("document.getElementById('bp-lv-sub').textContent"), f'{t}: right low text')
        ok('0.84 in / ft' in await pg.evaluate("document.getElementById('bp-lv-sub').textContent"), f'{t}: in/ft {await pg.evaluate("document.getElementById(\'bp-lv-sub\').textContent")}')
        tr = await pg.evaluate("document.getElementById('bp-lv-bub').style.transform")
        bx = float(tr.split('(')[1].split('px')[0])
        ok(bx < -20, f'{t}: bubble should move left {tr}')
        col = await pg.evaluate("getComputedStyle(document.getElementById('bp-lv-bub')).borderTopColor")
        ok(col=='rgb(10, 132, 255)', f'{t}: bubble not green when off {col}')
        # top raised (beta +3): bubble moves up (negative y), says Bottom low
        await tilt(pg, 3, 0)
        tr = await pg.evaluate("document.getElementById('bp-lv-bub').style.transform")
        by = float(tr.split(',')[1].split('px')[0])
        ok(by < -15, f'{t}: bubble up when top high {tr}')
        ok('Bottom low' in await pg.evaluate("document.getElementById('bp-lv-sub').textContent"), f'{t}: bottom low text')
        # Zero: current becomes level
        await pg.evaluate("bpLevelZero(false)"); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.getElementById('bp-lv-num').textContent")=='0.0°', f'{t}: zeroed')
        ok(await pg.evaluate("document.getElementById('bp-lv-reset').style.display")!='none', f'{t}: reset shown')
        await pg.evaluate("bpLevelZero(true)"); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.getElementById('bp-lv-num').textContent")=='3.0°', f'{t}: reset zero')
        # upright (phone standing) -> edge mode, tube vial
        await tilt(pg, 90, 0)
        ok(await pg.evaluate("!!document.querySelector('#bp-lv-stage .bp-lv-tube')"), f'{t}: tube vial when upright')
        ok(await pg.evaluate("document.getElementById('bp-lv-num').textContent")=='0.0°', f'{t}: upright level')
        # back to flat, smoothing never errors
        await tilt(pg, 0, 0)
        ok(await pg.evaluate("!!document.querySelector('#bp-lv-stage .bp-lv-flat')"), f'{t}: back to flat vial')
        await pg.screenshot(path='/tmp/lv_%s_%d.png' % (theme, w))
        await pg.evaluate("bpLevelClose()")
        ok(not await pg.evaluate("!!document.getElementById('bp-level')"), f'{t}: level closes')
        # ---------- COLOR ----------
        T = "window.bpColorTools"
        ok(await pg.evaluate(T+".deltaE('#FFFFFF','#FFFFFF')")==0, f'{t}: dE same')
        ok(95 < await pg.evaluate(T+".deltaE('#FFFFFF','#000000')") < 101, f'{t}: dE white-black')
        ok(await pg.evaluate(T+".deltaE('#808080','#828282')") < 2, f'{t}: dE near grays')
        ok(await pg.evaluate(T+".nearest([255,255,255])")=='White', f'{t}: nearest white')
        ok(await pg.evaluate(T+".nearest([22,22,22])")=='Black', f'{t}: nearest black')
        ok(await pg.evaluate(T+".nearest([188,178,164])")=='Greige', f'{t}: nearest greige')
        ok(await pg.evaluate(T+".hex([255,0,128.4])")=='#FF0080', f'{t}: hex')
        await pg.evaluate("document.getElementById('nav-colormatch').click()"); await pg.wait_for_timeout(1800)
        ok(await pg.evaluate("!!document.getElementById('bp-color')"), f'{t}: color opens')
        ok(await pg.evaluate("document.getElementById('bp-cm-vid').videoWidth>0"), f'{t}: camera feed')
        ok(await pg.evaluate("document.getElementById('bp-cm-msg').style.display")=='none', f'{t}: msg hidden once camera runs')
        live = await pg.evaluate("document.getElementById('bp-cm-hex').textContent")
        ok(live.startswith('#') and 'Looks like' in await pg.evaluate("document.getElementById('bp-cm-name').textContent"), f'{t}: live color {live!r}')
        await pg.evaluate("bpColorTake('A')"); await pg.evaluate("bpColorTake('B')"); await pg.wait_for_timeout(100)
        a = await pg.evaluate("document.querySelector('#bp-cm-A span').textContent"); b = await pg.evaluate("document.querySelector('#bp-cm-B span').textContent")
        ok(a.startswith('#') and b.startswith('#'), f'{t}: slots filled {a} {b}')
        res = await pg.evaluate("document.getElementById('bp-cm-res').textContent")
        ok('ΔE' in res, f'{t}: verdict shown {res!r}')
        # force a known match / mismatch through the verdict text
        await pg.evaluate("bpColorClear()")
        ok(await pg.evaluate("document.querySelector('#bp-cm-A span').textContent")=='Tap', f'{t}: clear')
        await pg.evaluate("bpColorWhite()"); await pg.wait_for_timeout(100)
        await pg.screenshot(path='/tmp/cm_%s_%d.png' % (theme, w))
        # tracks stop on close
        await pg.evaluate("window.__tr = document.getElementById('bp-cm-vid').srcObject.getTracks()")
        await pg.evaluate("bpColorClose()")
        ok(await pg.evaluate("window.__tr.every(t=>t.readyState==='ended')"), f'{t}: camera released on close')
        ok(not await pg.evaluate("!!document.getElementById('bp-color')"), f'{t}: color closes')
        # camera denied path
        await pg.evaluate("(()=>{navigator.mediaDevices.getUserMedia=function(){return Promise.reject(new Error('x'))};return 1})()")
        await pg.evaluate("bpColorOpen()"); await pg.wait_for_timeout(300)
        ok('blocked' in await pg.evaluate("document.getElementById('bp-cm-msg').textContent"), f'{t}: denied message')
        await pg.evaluate("bpColorClose()")
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await br.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8794','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
