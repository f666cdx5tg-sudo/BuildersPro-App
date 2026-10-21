"""BuildersPro v4.43 (Status / Space cells: faint ▾ so it is clear they open; no separate button).
Run from repo root: python3 test_v443.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs.push({id:'tj',name:'N. Peach St',status:'Active'});
['(F) Bathroom','Bedroom','Kitchen'].forEach((n,i)=>DB.rooms.push({id:'r'+i,jobId:'tj',name:n,type:'Other'}));
DB.punchlist.push({id:'p1',jobId:'tj',roomId:'r0',text:'Fix sink',title:'Fix sink',done:false});
window._bpPunchJob='tj';showScreen('s-punch');bpOpenPunchArea('r0');})()"""
CELL = "#bp-clf-punch .bp-pm"
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8785/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.43'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED); await pg.wait_for_timeout(600)
        ok(await pg.evaluate(f"document.querySelectorAll('{CELL}').length")==2, f'{t}: two cells')
        for i, name in ((1,'Status'),(2,'Space')):
            sel = f'{CELL}:nth-child({i})'
            info = await pg.evaluate(f"""(()=>{{var c=document.querySelector('{sel}'),a=getComputedStyle(c,'::after');
              var cr=c.getBoundingClientRect(),tr=c.querySelector('.bp-pm-t').getBoundingClientRect();
              return {{content:a.content,pe:a.pointerEvents,op:+a.opacity,w:parseFloat(a.width),right:parseFloat(a.right),cellRight:cr.right,textRight:tr.right,z:parseFloat(getComputedStyle(document.body).zoom)||1}}}})()""")
            ok(info['content'] not in ('none','normal'), f'{t}: {name} has a ▾')
            ok(info['pe']=='none', f'{t}: ▾ must not steal taps')
            ok(0 < info['op'] <= 0.7, f'{t}: ▾ should be faint (opacity {info["op"]})')
            chev_left = info['cellRight'] - (info['right'] + info['w'] + 4) * info['z']
            ok(info['textRight'] <= chev_left + 1, f'{t}: {name} text runs under the ▾ (text right {info["textRight"]:.0f} vs ▾ left {chev_left:.0f})')
            # still opens by tapping right on the ▾, and the ▾ flips + turns blue while open
            box = await (await pg.query_selector(sel)).bounding_box()
            await pg.mouse.click(box['x'] + box['width'] - 10, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
            ok(await pg.evaluate(f"document.querySelector('{sel} .bp-hm').classList.contains('open')"), f'{t}: tapping the ▾ opens {name}')
            tf = await pg.evaluate(f"getComputedStyle(document.querySelector('{sel}'),'::after').transform")
            ok(tf not in ('none',) and tf != await pg.evaluate("'matrix(0.707107, 0.707107, -0.707107, 0.707107, 0, 0)'"), f'{t}: ▾ should flip while open ({tf})')
            await pg.mouse.click(box['x'] + box['width'] - 10, box['y'] + box['height'] / 2); await pg.wait_for_timeout(250)
            ok(not await pg.evaluate(f"document.querySelector('{sel} .bp-hm').classList.contains('open')"), f'{t}: second tap closes {name}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await pg.screenshot(path=os.environ.get('SHOT_DIR','/tmp') + f'/chev_{theme}_{w}.png', clip={'x':0,'y':0,'width':w,'height':min(h,360)})
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8785','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for w,h in ((390,844),(834,1194)):
            for th in ('dark','light'): await run(w, h, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
