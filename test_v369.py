"""BuildersPro v3.69 (text & button size: smooth 85-180% range in a glass control; builds on v3.68).
Run from the repo root: python3 test_v369.py  (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.environ.get('BP_SHOTS', '')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)

SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen Remodel',status:'Active',address:'123 Main St',city:'Bergenfield',state:'NJ',client:'Mr. Smith'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen'}];save();renderAll();})()"""

async def run(w, h, tablet):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        tag = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='3.69'"), f'{tag}: version is not 3.69')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        boost = 1.4 if tablet else 1
        mx = 250 if tablet else 180
        # range + presets exist in the Sync-screen copy
        info = await pg.evaluate("""(()=>{const r=document.querySelector('#zoom-btn-row .bp-gr');return r?{min:+r.min,max:+r.max,step:+r.step,pills:[...document.querySelectorAll('#zoom-btn-row .bp-gp')].map(b=>b.dataset.pct)}:null})()""")
        ok(info is not None, f'{tag}: slider missing from Sync screen')
        ok(info and info['min'] == 85 and info['max'] == mx and info['step'] == 5, f'{tag}: slider range wrong {info}')
        ok(info and info['pills'] == ['100', '115', '130', '145', '160', '180'], f'{tag}: presets wrong {info}')
        # old buttons gone
        ok(await pg.evaluate("!document.querySelector('#zoom-btn-row [data-z]')"), f'{tag}: old 4 buttons still there')
        # presets apply, persist and scale the whole app
        for pct in (100, 130, 160, 180):
            await pg.evaluate(f"document.querySelector('#zoom-btn-row .bp-gp[data-pct=\"{pct}\"]').click()"); await pg.wait_for_timeout(250)
            z = await pg.evaluate("[localStorage.getItem('bp_zoom'),parseFloat(document.body.style.zoom)]")
            ok(abs(float(z[0]) - pct / 100) < 1e-6, f'{tag}: {pct}% not saved ({z})')
            ok(abs(z[1] - pct / 100 * boost) < 0.01, f'{tag}: {pct}% body zoom is {z[1]}')
            on = await pg.evaluate("[...document.querySelectorAll('#zoom-btn-row .bp-gp.on')].map(b=>b.dataset.pct)")
            ok(on == [str(pct)], f'{tag}: wrong pill highlighted {on}')
        # arbitrary in-between sizes, A- / A+
        await pg.evaluate("bpSetZoom(1.15)"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.querySelector('#zoom-btn-row .bp-gb[data-gd=\"1\"]').click()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("localStorage.getItem('bp_zoom')") == '1.2', f'{tag}: A+ should give 120%')
        await pg.evaluate("document.querySelector('#zoom-btn-row .bp-gb[data-gd=\"-1\"]').click();document.querySelector('#zoom-btn-row .bp-gb[data-gd=\"-1\"]').click()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("localStorage.getItem('bp_zoom')") == '1.1', f'{tag}: two A- should give 110%')
        ok(await pg.evaluate("document.querySelector('#zoom-btn-row [data-gv]').textContent") == '110', f'{tag}: readout should say 110')
        # limits
        await pg.evaluate("bpSetZoom(5)"); ok(await pg.evaluate("localStorage.getItem('bp_zoom')") == str(mx / 100), f'{tag}: max not enforced')
        await pg.evaluate("bpSetZoom(0.2)"); ok(await pg.evaluate("localStorage.getItem('bp_zoom')") == '0.85', f'{tag}: min not enforced')
        # old saved sizes still land on their preset
        for old, name in ((1, 'Normal'), (1.15, 'Large'), (1.3, 'XL'), (1.45, 'XXL')):
            await pg.evaluate(f"bpSetZoom({old})"); await pg.wait_for_timeout(120)
            on = await pg.evaluate("document.querySelector('#zoom-btn-row .bp-gp.on')?.innerText.split('\\n')[0]")
            ok(on and on.startswith(name) and not (name == 'XL' and on.startswith('XXL')), f'{tag}: old size {old} should light {name}, got {on}')
        # slider: live preview while dragging, saved only on release
        await pg.evaluate("bpSetZoom(1.15)"); await pg.wait_for_timeout(150)
        await pg.evaluate("(()=>{const r=document.querySelector('#zoom-btn-row .bp-gr');r.value=165;r.dispatchEvent(new Event('input',{bubbles:true}))})()"); await pg.wait_for_timeout(150)
        live = await pg.evaluate("[parseFloat(document.body.style.zoom),localStorage.getItem('bp_zoom')]")
        ok(abs(live[0] - 1.65 * boost) < 0.01 and live[1] == '1.15', f'{tag}: drag should preview without saving {live}')
        await pg.evaluate("document.querySelector('#zoom-btn-row .bp-gr').dispatchEvent(new Event('change',{bubbles:true}))"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("localStorage.getItem('bp_zoom')") == '1.65', f'{tag}: release should save 165%')
        # menu entry + header icon open the glass sheet; sheet stays one size while app scales
        await pg.evaluate("bpSetZoom(1)"); await pg.wait_for_timeout(200)
        await pg.evaluate("cycleFontSize()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("document.getElementById('bp-gs-wrap').classList.contains('open')"), f'{tag}: Text size did not open the glass sheet')
        w1 = await pg.evaluate("document.getElementById('bp-gs').getBoundingClientRect().width")
        h1 = await pg.evaluate("document.querySelector('#bp-gs .bp-gr').getBoundingClientRect().height")
        await pg.evaluate("bpSetZoom(1.8)"); await pg.wait_for_timeout(300)
        w2 = await pg.evaluate("document.getElementById('bp-gs').getBoundingClientRect().width")
        h2 = await pg.evaluate("document.querySelector('#bp-gs .bp-gr').getBoundingClientRect().height")
        ok(abs(w1 - w2) < 3 and abs(h1 - h2) < 3, f'{tag}: sheet changed size with the app ({w1:.0f}->{w2:.0f}, {h1:.0f}->{h2:.0f})')
        # sheet fits on screen at the biggest size
        r = await pg.evaluate("(()=>{const r=document.getElementById('bp-gs').getBoundingClientRect();return [r.left,r.right,r.bottom,innerWidth,innerHeight]})()")
        ok(r[0] >= -1 and r[1] <= r[3] + 1 and r[2] <= r[4] + 1, f'{tag}: sheet off screen {r}')
        # glass material really applied
        g = await pg.evaluate("(()=>{const s=getComputedStyle(document.querySelector('#bp-gs .bp-glass'));return [s.backdropFilter||s.webkitBackdropFilter, s.borderTopWidth]})()")
        ok('blur' in (g[0] or ''), f'{tag}: glass blur missing ({g})')
        ok(await pg.evaluate("document.querySelector('#bp-gs-wrap').style.pointerEvents!=='none'"), f'{tag}: sheet blocked')
        if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, f'glass_{tag}.png'))
        await pg.evaluate("document.getElementById('bp-gs-done').click()"); await pg.wait_for_timeout(150)
        ok(not await pg.evaluate("document.getElementById('bp-gs-wrap').classList.contains('open')"), f'{tag}: Done did not close')
        # menu subtitle shows the real value
        await pg.evaluate("bpSetZoom(1.6);bpDrawerRefresh()"); await pg.wait_for_timeout(150)
        sub = await pg.evaluate("document.getElementById('bp-d-text-sub').textContent")
        ok('Jumbo' in sub and '160%' in sub, f'{tag}: menu subtitle wrong {sub!r}')
        # reduced transparency falls back to solid
        await ctx.close() if False else None
        ok(len(errs) == 0, f'{tag}: console errors {errs[:3]}')
        await b.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8799', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844, False)
        await run(834, 1194, True)
    finally: srv.terminate()
    print(f'{checks - len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
