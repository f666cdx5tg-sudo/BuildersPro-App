import subprocess, time, asyncio, json
from playwright.async_api import async_playwright
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'GET,POST,PATCH','access-control-expose-headers':'x-oauth-scopes','content-type':'application/json'}
async def gh(route):
    u=route.request.url; m=route.request.method
    if m=='OPTIONS': return await route.fulfill(status=204, headers=CORS)
    if u.endswith('/user'): return await route.fulfill(status=200, headers={**CORS,'x-oauth-scopes':'gist'}, body=json.dumps({'login':'stan'}))
    if '/gists/oldgist' in u and m=='GET': return await route.fulfill(status=200, headers=CORS, body=json.dumps({'id':'oldgist','owner':{'login':'someoneelse'},'files':{}}))
    if u.endswith('/gists') and m=='POST': return await route.fulfill(status=201, headers=CORS, body=json.dumps({'id':'newgist1234567890abcdef','files':{}}))
    if m=='PATCH': return await route.fulfill(status=403, headers=CORS, body='')
    return await route.fulfill(status=200, headers=CORS, body=json.dumps({'id':'newgist1234567890abcdef','files':{}}))
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8818','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/api.github.com/**', gh)
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','apple-cloudkit')) else r.fallback())
            await pg.goto('http://localhost:8818/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); _syncToken='ghp_old'; _syncGistId='oldgist'; changeTokenPrompt()")
            await pg.fill('#bsp-token-in','ghp_'+'A'*36); await pg.locator('#bsp-token-save').tap(); await pg.wait_for_timeout(1200)
            print('check shown:\n', await pg.evaluate("document.getElementById('bsp-token-err')?.textContent"))
            await pg.wait_for_timeout(5000)
            print('gist now:',await pg.evaluate("_syncGistId"),'| last GH:',await pg.evaluate("JSON.stringify(BP_LAST_GH&&{s:BP_LAST_GH.status,step:BP_LAST_GH.step})"))
            await pg.wait_for_timeout(3000)
            print('pill:',await pg.evaluate("document.getElementById('bp-q-chip').textContent"), errs[:2])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
