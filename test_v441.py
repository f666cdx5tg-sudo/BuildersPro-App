"""BuildersPro v4.41 (Punch: Status / Space cells open on tap with no ••• button; option lists never cut off at the screen edge).
Run from repo root: python3 test_v441.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs.push({id:'tj',name:'N. Peach St',status:'Active'});
['(F) Bathroom','Bedroom','Front Roof','Gutters','Front Door','Side Door','Driveway','Front Steps','Sidewalk','Windows (Ext)','Garage','Basement','Kitchen','Attic'].forEach((n,i)=>DB.rooms.push({id:'r'+i,jobId:'tj',name:n,type:'Other'}));
DB.punchlist.push({id:'p1',jobId:'tj',roomId:'r0',text:'Fix sink',title:'Fix sink',done:false});
window._bpPunchJob='tj';showScreen('s-punch');bpOpenPunchArea('r0');})()"""
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8793/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.44'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED); await pg.wait_for_timeout(600)
        ok(await pg.evaluate("document.querySelectorAll('#bp-clf-punch .bp-pm').length")==2, f'{t}: Status + Space cells')
        # no visible ••• button inside the cells
        ok(await pg.evaluate("[...document.querySelectorAll('#bp-clf-punch .bp-pm svg.bp-dots')].every(s=>getComputedStyle(s).display==='none')"), f'{t}: dots icon still visible in a cell')
        # the invisible button covers the whole cell
        cov = await pg.evaluate("[...document.querySelectorAll('#bp-clf-punch .bp-pm')].map(c=>{var a=c.getBoundingClientRect(),b=c.querySelector('.bp-hm-btn').getBoundingClientRect();return Math.abs(a.width-b.width)<=4&&Math.abs(a.height-b.height)<=4&&getComputedStyle(c.querySelector('.bp-hm-btn')).backgroundColor==='rgba(0, 0, 0, 0)'})")
        ok(all(cov), f'{t}: button should cover the whole cell, invisible {cov}')
        # a real tap in the middle of the cell text opens the list (Playwright hits whatever is on top)
        for i, name in ((1, 'Status'), (2, 'Space')):
            sel = f'#bp-clf-punch .bp-pm:nth-child({i})'
            box = await (await pg.query_selector(sel)).bounding_box()
            await pg.mouse.click(box['x'] + box['width'] * 0.3, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
            ok(await pg.evaluate(f"document.querySelector('{sel} .bp-hm').classList.contains('open')"), f'{t}: tapping {name} cell text opens it')
            # list fully on screen horizontally
            r = await pg.evaluate(f"(()=>{{var r=document.querySelector('{sel} .bp-hm-pop').getBoundingClientRect();return [r.left,r.right,document.documentElement.clientWidth]}})()")
            ok(r[0] >= 0 and r[1] <= r[2], f'{t}: {name} list cut off {r}')
            # tapping the same cell again closes it
            await pg.mouse.click(box['x'] + box['width'] * 0.3, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
            ok(not await pg.evaluate(f"document.querySelector('{sel} .bp-hm').classList.contains('open')"), f'{t}: second tap on {name} closes')
        # Space list: long, scrolls, items selectable, applies filter, tapped item text visible not under dock
        sel = '#bp-clf-punch .bp-pm:nth-child(2)'
        box = await (await pg.query_selector(sel)).bounding_box()
        await pg.mouse.click(box['x'] + box['width'] * 0.3, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
        z = float(await pg.evaluate("getComputedStyle(document.body).zoom") or 1)
        ph = await pg.evaluate(f"document.querySelector('{sel} .bp-hm-pop').getBoundingClientRect().height")
        ok(ph <= h * 0.62, f'{t}: long Space list should be capped and scroll (height {ph} of {h})')
        bot = await pg.evaluate(f"document.querySelector('{sel} .bp-hm-pop').getBoundingClientRect().bottom")
        ok(bot <= h - 90, f'{t}: Space list runs under the bottom buttons (bottom {bot} of {h})')
        ok(await pg.evaluate(f"(()=>{{var p=document.querySelector('{sel} .bp-hm-pop');return p.scrollHeight>p.clientHeight}})()"), f'{t}: Space list should be scrollable')
        await pg.evaluate(f"[...document.querySelectorAll('{sel} .bp-hm-it')].find(b=>b.innerText.includes('Bedroom')).click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("window._bpClFilter.space")=='r1', f'{t}: choosing a space applies the filter')
        ok('Bedroom' in await pg.evaluate("document.querySelector('#bp-clf-punch .bp-pm:nth-child(2) .bp-pm-t').innerText"), f'{t}: Space cell shows the chosen space')
        ok(not await pg.evaluate("document.querySelector('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm').classList.contains('open')"), f'{t}: list closes after choosing')
        # Status: choose Complete
        sel1 = '#bp-clf-punch .bp-pm:nth-child(1)'
        box = await (await pg.query_selector(sel1)).bounding_box()
        await pg.mouse.click(box['x'] + 20, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
        await pg.evaluate(f"[...document.querySelectorAll('{sel1} .bp-hm-it')].find(b=>b.innerText.trim()==='Complete').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("window._bpClFilter.show")=='done', f'{t}: Status Complete applies')
        # Select button still works and cells still ~46px tall
        ok(await pg.evaluate("!!document.querySelector('#bp-clf-punch .bp-selbtn')"), f'{t}: Select button present')
        hh = await pg.evaluate("document.querySelector('#bp-clf-punch .bp-pm').getBoundingClientRect().height")
        ok(hh / z >= 43.5, f'{t}: cell tap height {hh / z}')
        # edge-guard: simulate a list that would hang off the left
        await pg.evaluate("document.querySelector('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm-pop').style.minWidth='700px'")
        await pg.evaluate("bpHMenuClose();bpHMenuToggle(document.querySelector('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm').id)"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("(()=>{var r=document.querySelector('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm-pop').getBoundingClientRect();return [r.left,r.right]})()")
        ok(r[0] >= 9, f'{t}: edge guard did not pull an over-wide list back in {r}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8793','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
