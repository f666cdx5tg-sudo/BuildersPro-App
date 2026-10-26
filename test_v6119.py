"""v6.1.19 — red 'iCloud not syncing' bar + GitHub token parked while iCloud is on (both apps)."""
import subprocess, time, asyncio, json
from playwright.async_api import async_playwright
BLOCK=('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')
fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
async def run(b, page, vp, shell, pre):
    ctx=await b.new_context(viewport=vp)
    init=("window.BPShell={version:'t'};" if shell else "")+pre
    await ctx.add_init_script(init)
    pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:8823/'+page); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')?.remove()")
    return ctx,pg,errs
async def bar(pg):
    await pg.evaluate("bpCkWarnPaint()")
    return await pg.evaluate("(function(){var b=document.getElementById('bp-ck-warn');return b&&b.classList.contains('on')?b.innerText:''})()")
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8823'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            for page,vp,tag in (('index.html',{'width':390,'height':844},'field'),('desktop.html',{'width':1280,'height':820},'desk')):
                # iCloud on, token saved, signed out (the iPhone case)
                pre="localStorage.setItem('bp_ck_on','1');localStorage.setItem('bp_sync',JSON.stringify({token:'ghp_old',gistId:'g1'}));"
                ctx,pg,errs=await run(b,page,vp,True,pre)
                await pg.wait_for_timeout(2200)
                ok(await pg.evaluate("_syncToken")=='',tag+': GitHub token parked while iCloud on')
                ok(await pg.evaluate("localStorage.getItem('bp_gh_parked')")=='ghp_old',tag+': token kept in bp_gh_parked')
                ok(json.loads(await pg.evaluate("localStorage.getItem('bp_sync')")).get('gistId')=='g1',tag+': other sync settings untouched')
                await pg.evaluate("bpCk.state.user=null;bpCk.state.authChecked=true")
                t=await bar(pg); ok('signed out' in t,tag+': red bar when signed out ('+t.strip()[:50]+')')
                await pg.evaluate("bpCk.state.authChecked=false")
                ok(await bar(pg)=='',tag+': no bar before the sign-in check has answered')
                await pg.evaluate("bpCk.state.user={userRecordName:'u'};bpCk.state.authChecked=true")
                ok(await bar(pg)=='',tag+': bar gone once signed in')
                await pg.evaluate("bpCk.state.user=null;bpCk.state.authChecked=true")
                await pg.click('#bp-ck-warn'); await pg.wait_for_timeout(600)
                ok(await pg.evaluate("!!document.getElementById('bp-cksync-card')&&!!document.getElementById('bp-cksync-card').offsetParent"),tag+': tapping bar opens Sync with the iCloud card')
                ok(await bar(pg)=='',tag+': bar steps aside while Sync card is on screen')
                await pg.screenshot(path='/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/'+tag+'_sync.png')
                ok(not errs,tag+': no page errors '+str(errs[:2]))
                await ctx.close()
                # iCloud off inside the native app → warns; in plain web → silent
                ctx,pg,errs=await run(b,page,vp,True,"localStorage.removeItem('bp_ck_on');")
                t=await bar(pg); ok('off' in t,tag+': native app warns when iCloud is off ('+t.strip()[:45]+')')
                await ctx.close()
                ctx,pg,errs=await run(b,page,vp,False,"localStorage.removeItem('bp_ck_on');localStorage.setItem('bp_sync',JSON.stringify({token:'ghp_keep'}));")
                await pg.wait_for_timeout(2200)
                ok(await bar(pg)=='',tag+': plain web copy with iCloud off stays quiet')
                ok(await pg.evaluate("_syncToken")=='ghp_keep',tag+': token NOT parked when iCloud is off')
                await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d failures'%len(fails))
asyncio.run(main())
