"""BuildersPro v3.70 (no clipped dollar amounts at big text sizes; builds on v3.69).
Run from the repo root: python3 test_v370.py  (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)

SEED = """(()=>{
DB.jobs=[{id:'j1',name:'Smith Kitchen Remodel',status:'Active',address:'123 Main Street Apt 4B',city:'Bergenfield',state:'NJ',zip:'07621',client:'Mr. Smith',contract:148000,created:new Date().toISOString()},
{id:'j2',name:'Rosenberg Bathroom Gut Renovation',status:'Active',contract:1250000,client:'Rosenberg Holdings LLC'}];
DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen'}];
DB.expenses=[{id:'e1',jobId:'j1',desc:'Copper fittings and pipe',amount:12480.55,date:'2026-10-08',category:'Materials',vendor:'Ferguson Plumbing Supply'},{id:'e2',jobId:'j2',desc:'Fixtures',amount:98765.43,date:'2026-10-07',category:'Materials'}];
DB.invoices=[{id:'i1',jobId:'j1',number:'INV-1001',amount:48000,status:'Sent',date:'2026-10-01',desc:'Progress billing 1'}];
DB.payments=[{id:'pm1',jobId:'j1',amount:24000,date:'2026-10-03',method:'Check'}];
DB.contractors=[{id:'c1',jobId:'j1',name:'ABC Electric Contractors Inc',trade:'Electrical',value:32500}];
DB.changeOrders=[{id:'co1',jobId:'j1',desc:'Add island sink',amount:6850,status:'Pending'}];
save();renderAll();})()"""
SCREENS = [('home', "showScreen('s-home')"), ('jobs', "showScreen('s-jobs')"), ('job1', "openJobDetail('j1')"), ('job2', "openJobDetail('j2')"),
           ('fin-inv', "showScreen('s-finance');setFinanceTab('invoices')"), ('fin-exp', "setFinanceTab('expenses')"), ('fin-pay', "setFinanceTab('payments')")]
# a dollar amount that is cut off: its own box clips it, it sits past the screen edge, or an ancestor with overflow:hidden cuts it
CLIPPED = """(()=>{const out=[],vw=innerWidth,M=/^[\\s\\-−+(]*\\$\\s?[\\d,]+(\\.\\d+)?[\\s)]*$/;
document.querySelectorAll('.screen.active *').forEach(e=>{
  if(e.childNodes.length!==1||e.firstChild.nodeType!==3||!M.test(e.textContent))return;
  const r=e.getBoundingClientRect();if(!r.width)return;const cs=getComputedStyle(e);
  let bad=(e.scrollWidth>e.clientWidth+1&&cs.overflowX!=='visible')||r.right>vw+1||r.left<-1;
  let a=e.parentElement;while(!bad&&a&&a!==document.body){const ac=getComputedStyle(a);if(ac.overflowX!=='visible'){const ar=a.getBoundingClientRect();if(r.right>ar.right+1||r.left<ar.left-1)bad=true}a=a.parentElement}
  if(bad)out.push(e.textContent.trim())});return out})()"""

async def run(w, h, zooms):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        tag = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='3.70'"), f'{tag}: version is not 3.70')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        for z in zooms:
            await pg.evaluate(f"bpSetZoom({z})"); await pg.wait_for_timeout(500)
            for name, js in SCREENS:
                await pg.evaluate(js); await pg.wait_for_timeout(900)
                bad = await pg.evaluate(CLIPPED)
                ok(not bad, f'{tag} z={z} {name}: clipped dollar amounts {bad}')
            # job screen details
            await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(900)
            meta = await pg.evaluate("(()=>{const m=document.getElementById('jd-meta');const r=m.getBoundingClientRect();const st=[...m.querySelectorAll('b')].pop();const sr=st&&st.getBoundingClientRect();return {t:m.innerText,right:sr&&sr.right,vw:innerWidth}})()")
            ok('Active' in meta['t'] and meta['right'] is not None and meta['right'] <= meta['vw'] + 1, f'{tag} z={z}: job status cut off {meta}')
            btn = await pg.evaluate("(()=>{const b=[...document.querySelectorAll('#jd-walkthrough-section button')][0];if(!b)return null;const r=b.getBoundingClientRect();return {right:r.right,vw:innerWidth}})()")
            ok(btn is None or btn['right'] <= btn['vw'] + 1, f'{tag} z={z}: New Inspection button off screen {btn}')
            # backup reminder: text and button must not overlap
            await pg.evaluate("localStorage.removeItem('bp_backup_snooze');showScreen('s-home');window.bpPaintBackupNag&&bpPaintBackupNag()"); await pg.wait_for_timeout(700)
            ov = await pg.evaluate("""(()=>{const n=document.getElementById('bp-backup-nag');if(!n)return null;const t=n.firstElementChild.firstElementChild,bt=n.querySelector('button');const a=t.getBoundingClientRect(),c=bt.getBoundingClientRect();
              return {overlap:!(a.right<=c.left+1||c.right<=a.left+1||a.bottom<=c.top+1||c.bottom<=a.top+1),tw:a.width}})()""")
            ok(ov is not None and not ov['overlap'] and ov['tw'] > 120, f'{tag} z={z}: backup banner text and button collide {ov}')
        # shrink-to-fit is proportional and reversible
        await pg.evaluate("bpSetZoom(1.8)"); await pg.evaluate("openJobDetail('j2')"); await pg.wait_for_timeout(1000)
        fs = await pg.evaluate("""(()=>{const e=[...document.querySelectorAll('.screen.active *')].find(x=>x.childNodes.length===1&&x.firstChild.nodeType===3&&x.textContent.trim()==='$1,151,234.57'&&getComputedStyle(x).overflowX==='hidden');return e?[parseFloat(getComputedStyle(e).fontSize),e.__bpBase]:null})()""")
        ok(fs is not None and fs[1] and 0.54 * fs[1] <= fs[0] <= fs[1] and (fs[0] < fs[1] or w >= 700), f'{tag}: long amount did not shrink within limits {fs}  (the iPad has room, so it may stay full size)')
        await pg.evaluate("bpSetZoom(1)"); await pg.wait_for_timeout(1000)
        fs2 = await pg.evaluate("""(()=>{const e=[...document.querySelectorAll('.screen.active *')].find(x=>x.childNodes.length===1&&x.firstChild.nodeType===3&&x.textContent.trim()==='$1,151,234.57'&&getComputedStyle(x).overflowX==='hidden');return e?parseFloat(getComputedStyle(e).fontSize):null})()""")
        ok(fs2 is not None and fs[1] and abs(fs2 - fs[1]) < 0.6, f'{tag}: amount did not grow back at Normal size ({fs2} vs {fs and fs[1]})')
        # short amounts are never shrunk
        sm = await pg.evaluate("""(()=>{const e=[...document.querySelectorAll('.screen.active *')].find(x=>x.childNodes.length===1&&x.firstChild.nodeType===3&&x.textContent.trim()==='$0');return e?[parseFloat(getComputedStyle(e).fontSize),e.__bpBase||null]:null})()""")
        ok(sm is None or sm[1] is None or abs(sm[0] - sm[1]) < 0.6, f'{tag}: a short amount was shrunk {sm}')
        ok(len(errs) == 0, f'{tag}: console errors {errs[:3]}')
        await b.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8799', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844, [1.15, 1.45, 1.8])
        await run(834, 1194, [1.0, 1.45, 2.0])
    finally: srv.terminate()
    print(f'{checks - len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
