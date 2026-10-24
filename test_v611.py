"""BuildersPro v6.1.1 (clients in the field phone book). Run: python3 test_v611.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
    else: print('  ok  ', m)

SEED = """(function(){
  DB.jobs.push({id:'jA',name:'Lee Bath',status:'Active',client:'Ann Lee',address:'12 Elm St',clientEmail:'ann@x.com',clientPhone:'2015550100'});
  DB.jobs.push({id:'jB',name:'Lee Kitchen With A Very Long Name For Wrapping Checks',status:'Active',client:'Ann Lee',address:'12 Elm St',clientEmail:'ann@x.com',clientPhone:'2015550100'});
  DB.jobs.push({id:'jC',name:'Diaz Deck',status:'Active',client:'Bo Diaz',address:'9 Oak Ave',clientEmail:'',clientPhone:'2015550111'});
  DB.jobs.forEach(function(j){ bspSyncClientContact(j); });
  DB.contacts.push({id:'s1',type:'Contractor',name:'Mike Pipes',company:'Pipes LLC',phone:'2015550199',skills:['Plumbing'],created:new Date().toISOString()});
  save(); bpPhoneBookOpen();
})()"""

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8794', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page()
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8794/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION") == '6.1.1', 'version is 6.1.1')
            await pg.evaluate(SEED); await pg.wait_for_timeout(600)
            seg = await pg.evaluate("document.getElementById('bsp-pb-seg')?.innerText||''")
            ok('Subs' in seg and 'Clients (2)' in seg, 'phone book has Subs | Clients (2): ' + seg.replace('\n', ' | '))
            body = await pg.evaluate("document.getElementById('s-finance').innerText")
            ok('Mike Pipes' in body and 'Ann Lee' not in body, 'opens on Subs, as before')
            await pg.locator('#bsp-pb-seg button', has_text='Clients').tap(); await pg.wait_for_timeout(400)
            lst = await pg.evaluate("document.getElementById('bsp-cl-list')?.innerText||''")
            ok('Ann Lee' in lst and 'Bo Diaz' in lst and 'Mike Pipes' not in lst, 'Clients view lists clients only')
            ok(lst.count('Ann Lee') == 1 and 'Lee Bath' in lst and 'Lee Kitchen' in lst, 'same client on 2 jobs = one card, both jobs listed')
            ok(await pg.evaluate("!!document.querySelector('#bsp-cl-list a[href=\"tel:2015550100\"]')"), 'cell is tap-to-call')
            ok(await pg.evaluate("!!document.querySelector('#bsp-cl-list a[href=\"mailto:ann@x.com\"]')"), 'email is tap-to-email')
            wrap = await pg.evaluate("""()=>[...document.querySelectorAll('#bsp-cl-list span')].filter(s=>s.textContent.startsWith('Lee Kitchen')).every(s=>s.getBoundingClientRect().height<26)""")
            ok(wrap, 'long job name stays on one line')
            await pg.screenshot(path='/tmp/v611_clients.png')
            await pg.fill('#bsp-cl-q', 'oak'); await pg.wait_for_timeout(200)
            lst = await pg.evaluate("document.getElementById('bsp-cl-list').innerText")
            ok('Bo Diaz' in lst and 'Ann Lee' not in lst, 'search finds by address')
            await pg.fill('#bsp-cl-q', ''); await pg.wait_for_timeout(200)
            await pg.locator('#bsp-cl-list div', has_text='Diaz Deck').last.tap(); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("document.getElementById('s-job-detail').classList.contains('active') && currentJobId==='jC'"), 'tapping a job opens it')
            await pg.evaluate("bpPhoneBookOpen()"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("document.querySelector('#bsp-pb-seg button.on').textContent") == 'Subs', 'reopening the phone book starts on Subs')
            ok(not errs, 'no page errors: ' + str(errs[:3]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
