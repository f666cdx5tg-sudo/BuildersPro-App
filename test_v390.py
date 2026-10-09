import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto("http://localhost:8799/desktop.html"); await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(600)
        await pg.evaluate("""()=>{DB.jobs.push({id:'jobX',name:'Peach',status:'active'});DB.rooms.push({id:'r1',jobId:'jobX',name:'Kitchen',type:'Kitchen'});
          (DB.punchlist=DB.punchlist||[]).push({id:'p1',jobId:'jobX',roomId:'r1',text:'x',done:true});showView('jobs');renderDesktopJobDetail('jobX')}""")
        await pg.wait_for_timeout(800)
        r=await pg.evaluate("[...document.querySelectorAll('div')].filter(d=>d.textContent.trim().endsWith('areas fully done')&&d.children.length<=1).map(d=>({svg:d.querySelectorAll('svg').length,txt:d.textContent.trim()}))")
        print(r, errs[:2])
        await b.close()
asyncio.run(main())
