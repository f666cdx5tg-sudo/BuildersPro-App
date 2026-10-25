import subprocess, time, asyncio, json
from playwright.async_api import async_playwright
SHIM="""window.__cal=[]; window.BPShell={version:'t'}; window.webkit={messageHandlers:{bp:{postMessage:function(m){ if(m.kind==='calendarSync'){ __cal.push(m.events); setTimeout(function(){ bpCalDone({ok:true,total:m.events.length,added:m.events.length,changed:0,removed:0,where:'iCloud'}) },5);} }}}};"""
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8820','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); await ctx.add_init_script(SHIM)
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8820/index.html'); await pg.wait_for_timeout(2000)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); DB.jobs=[{id:'j1',name:'Shedwick',address:'634 N. Shedwick St',city:'Philadelphia',state:'PA'}]; DB.appointments=[{id:'a_1',jobId:'j1',date:'2026-10-27',time:'09:30',title:'Rough plumbing inspection',type:'Inspection'},{id:'a-2',date:'2026-10-29',title:'Delivery',type:'Delivery'}]; save();")
            await pg.wait_for_timeout(9000)
            await pg.evaluate("openSync()"); await pg.wait_for_timeout(400)
            print('sent:',json.dumps(await pg.evaluate("__cal[__cal.length-1]"))[:400])
            print('posts:',await pg.evaluate("__cal.length"),'| card:',await pg.evaluate("document.getElementById('bp-cal-native')?.innerText"),errs[:2])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
