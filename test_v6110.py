import subprocess, time, asyncio
from playwright.async_api import async_playwright
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8813','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            dialogs=[]; pg.on('dialog', lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8813/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); _syncToken='ghp_old_xxxxxxxx'; openSync()"); await pg.wait_for_timeout(400)
            await pg.locator('#bsp-change-token').tap(); await pg.wait_for_timeout(400)
            sheet=await pg.evaluate("!!document.getElementById('bsp-token-sheet')")
            await pg.fill('#bsp-token-in','github_pat_abc123456789'); await pg.locator('#bsp-token-save').tap()
            e1=await pg.evaluate("document.getElementById('bsp-token-err').textContent")
            await pg.fill('#bsp-token-in','ghp_NEWTOKEN1234567890'); await pg.locator('#bsp-token-save').tap(); await pg.wait_for_timeout(600)
            print('v',await pg.evaluate("APP_VERSION"),'| sheet opens:',sheet,'| no prompt box used:',not dialogs,'| fine-grained refused:',e1[:40],'| saved:',await pg.evaluate("_syncToken"),'| closed:',await pg.evaluate("!document.getElementById('bsp-token-sheet')"),errs[:2])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
