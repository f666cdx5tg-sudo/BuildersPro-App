import asyncio, re
from playwright.async_api import async_playwright
ROOMS=[("Sidewalk","Exterior"),("Foyer","Other"),("Basement/ mechanical","Basement"),("Driveway","Exterior"),("Front Steps","Exterior"),("Family Room","Living Room"),("Kitchen","Kitchen")]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto("http://localhost:8799/desktop.html"); await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(600)
        res=await pg.evaluate("""(rs)=>{DB.jobs=DB.jobs||[];DB.jobs.push({id:'jobX',name:'Peach',status:'active'});
          DB.rooms=DB.rooms||[];rs.forEach((r,i)=>DB.rooms.push({id:'r'+i,jobId:'jobX',name:r[0],type:r[1]}));
          try{showView('jobs')}catch(e){}
          renderDesktopJobDetail('jobX');
          var out=[];document.querySelectorAll('#view-jobs .card, .card').forEach(c=>{var s=c.querySelector('span[style*="font-size:20px"]');var n=s&&s.nextElementSibling;if(n&&rs.some(r=>r[0]===n.textContent))out.push([n.textContent,s.innerHTML.slice(0,40)])});return out}""",[list(r) for r in ROOMS])
        for r in res: print(r)
        print(errs[:3])
        await b.close()
asyncio.run(main())
