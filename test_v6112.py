import subprocess, time, asyncio
from playwright.async_api import async_playwright
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8814','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8814/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); _syncToken='ghp_x'; _lastSyncError='Push failed: Unexpected error from GitHub. (HTTP 403)'; var c=document.getElementById('bp-q-chip'); c.textContent='⚠️ Sync failed'; c.classList.add('on')")
            await pg.wait_for_timeout(500)
            t=await pg.evaluate("document.getElementById('bp-q-chip').textContent")
            await pg.locator('#bp-q-chip').tap(); await pg.wait_for_timeout(400)
            print('chip:',t,'| token sheet opened:',await pg.evaluate("!!document.getElementById('bsp-token-sheet')"),errs[:2])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
