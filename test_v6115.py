import subprocess, time, asyncio, json
from playwright.async_api import async_playwright
SP=__import__('os').path.dirname(__import__('os').path.abspath(__file__))+'/'   # big.json from tools/make_test_fixtures.py
SHIM = """
window.__bk = {parts:[], begin:null};
window.BPShell = {version:'t'};
window.webkit = {messageHandlers:{bp:{postMessage:function(m){
  if (m.kind==='backupBegin') { __bk.begin=m.name; __bk.parts=[]; }
  else if (m.kind==='backupChunk') { __bk.parts.push(m.text); __bk.maxPart=Math.max(__bk.maxPart||0,m.text.length); }
  else if (m.kind==='backupEnd') { var t=__bk.parts.join(''); __bk.size=t.length; try{ var o=JSON.parse(t); __bk.jobs=o.db.jobs.length; __bk.refsLeft=(t.match(/"bpb:/g)||[]).length; __bk.dataUrls=(t.match(/"data:/g)||[]).length; }catch(e){ __bk.parseErr=e.message; }
     setTimeout(function(){ bpBackupDone({ok:true, where:'iCloud Drive › BuildersPro › Backups', name:__bk.begin, bytes:t.length}); },10); }
}}}};
"""
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8819','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            await ctx.add_init_script(SHIM)
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8819/index.html'); await pg.wait_for_timeout(2500)
            print('token cleared:', await pg.evaluate("_syncToken===''"))
            data=open(SP+'big.json').read()
            await pg.evaluate("d=>{document.getElementById('bp-lock')?.remove(); var o=JSON.parse(d); DB=o.db; ensureDbShape();}", data)
            src_photos = await pg.evaluate("(function(){var b={}; bpSplitBlobs(DB,b); return Object.keys(b).length})()")
            r=await pg.evaluate("bpDailyFileNow()")
            bk=await pg.evaluate("({name:__bk.begin,size:__bk.size,jobs:__bk.jobs,refsLeft:__bk.refsLeft,dataUrls:__bk.dataUrls,maxPart:__bk.maxPart,err:__bk.parseErr})")
            await pg.evaluate("openSync()"); await pg.wait_for_timeout(300)
            card=await pg.evaluate("document.getElementById('bp-daily-file')?.innerText")
            print('result',r,'| photos in DB',src_photos,'| file',bk,'\ncard:',card,errs[:2])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
