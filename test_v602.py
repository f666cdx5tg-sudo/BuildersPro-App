"""BuildersPro v6.0.2 (Change order in two taps: On Site card row + job page button).
Run from repo root: python3 test_v602.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
    else: print('  ok  ', m)

SEED = """(function(){
  DB.jobs.push({id:'jA',name:'Smith Reno',status:'active',contract:50000});
  DB.jobs.push({id:'jB',name:'Other Job',status:'active',contract:1000});
  DB.changeOrders=DB.changeOrders||[];
  DB.changeOrders.push({id:'c1',jobId:'jA',number:'CO-1',amount:2500,status:'Approved',created:new Date().toISOString()});
  DB.changeOrders.push({id:'c2',jobId:'jA',number:'CO-2',amount:800,status:'Submitted',created:new Date().toISOString()});
  DB.changeOrders.push({id:'c3',jobId:'jB',number:'CO-9',amount:999,status:'Submitted',created:new Date().toISOString()});
  save(); bpSetActiveJob('jA'); showScreen('s-home'); renderHome();
})()"""

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8792', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page()
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8792/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION") == '6.0.2', 'version is 6.0.2')
            await pg.evaluate(SEED); await pg.wait_for_timeout(800)

            # --- On Site card row ---
            row = pg.locator('#bp-onsite-card [data-onsite="co"]')
            ok(await row.count() == 1, 'On Site card shows the Change order row')
            txt = (await row.inner_text()).replace('\n', ' ')
            ok('Change order' in txt, 'row is labelled "Change order": ' + txt)
            ok('1 waiting' in txt and 'CO-9' not in txt, 'row shows 1 waiting (job A only, not job B): ' + txt)
            col = await row.evaluate("e=>getComputedStyle(e.querySelector('span')).color")
            ok(col == 'rgb(191, 90, 242)', 'row label is purple: ' + col)
            grid_then_row = await pg.evaluate("""()=>{var c=document.getElementById('bp-onsite-card');var g=c.querySelector('[data-onsite="money"]').parentNode;return g.nextElementSibling&&g.nextElementSibling.getAttribute('data-onsite')==='co'}""")
            ok(grid_then_row, 'row sits right under the three tiles')
            await pg.screenshot(path='/tmp/v602_home.png')
            await row.tap(); await pg.wait_for_timeout(600)
            sheet_job = await pg.evaluate("""()=>{var s=document.querySelector('#co-job, [id^="co-"] select, select#co-job');var m=[...document.querySelectorAll('select')].find(x=>x.value==='jA');return m?m.value:(s?s.value:'')}""")
            visible = await pg.evaluate("()=>!!document.querySelector('[onclick*=\"saveChangeOrder\"]')")
            ok(visible, 'tapping the row opens the change-order sheet')
            ok(sheet_job == 'jA', 'sheet is pre-scoped to the On Site job: ' + str(sheet_job))
            await pg.screenshot(path='/tmp/v602_sheet.png')
            # save a new one through the sheet and check the Home row updates
            await pg.evaluate("document.getElementById('co-title').value='Extra outlet'; document.getElementById('co-amount').value='1200'")
            before = await pg.evaluate("(DB.changeOrders||[]).length")
            await pg.evaluate("saveChangeOrder()"); await pg.wait_for_timeout(700)
            after = await pg.evaluate("(DB.changeOrders||[]).length")
            ok(after == before + 1, 'change order saved from the sheet (%d -> %d)' % (before, after))
            ok(await pg.evaluate("(DB.changeOrders||[]).slice(-1)[0].jobId") == 'jA', 'new change order belongs to job A')
            txt2 = (await pg.locator('#bp-onsite-card [data-onsite="co"]').inner_text()).replace('\n', ' ')
            ok('2 waiting' in txt2, 'Home row refreshed after save: ' + txt2)

            # --- job page button ---
            await pg.evaluate("document.getElementById('co-modal')?.remove()"); await pg.evaluate("openJobDetail('jA')"); await pg.wait_for_timeout(700)
            btn = pg.locator('#jd-act-co')
            ok(await btn.count() == 1 and await btn.is_visible(), 'job page has the Change Order quick-action button')
            col2 = await btn.evaluate("e=>getComputedStyle(e).color")
            ok(col2 == 'rgb(191, 90, 242)', 'job page button is purple: ' + col2)
            n = await pg.evaluate("document.querySelectorAll('#s-job-detail .bp-act-row .bp-act').length")
            ok(n == 4, '4 quick actions on the job page: %d' % n)
            wrap = await pg.evaluate("""()=>[...document.querySelectorAll('#s-job-detail .bp-act-row .bp-act')].every(b=>b.getBoundingClientRect().width>40)""")
            ok(wrap, 'all four quick actions still fit on an iPhone width')
            await pg.screenshot(path='/tmp/v602_job.png')
            await btn.tap(); await pg.wait_for_timeout(600)
            ok(await pg.evaluate("()=>!!document.querySelector('[onclick*=\"saveChangeOrder\"]')"), 'job page button opens the change-order sheet')

            # --- no job on site: no row, no errors ---
            await pg.evaluate("bpSetActiveJob(''); showScreen('s-home'); renderHome()"); await pg.wait_for_timeout(500)
            ok(await pg.locator('#bp-onsite-card').count() == 0, 'no On Site card (and no row) when no job is on site')
            ok(not errs, 'no page errors: ' + '; '.join(errs)[:300])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d/%d passed' % (checks - len(fails), checks))
    sys.exit(1 if fails else 0)

asyncio.run(main())
