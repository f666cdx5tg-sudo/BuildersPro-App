import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto("http://localhost:8799/desktop.html"); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("DB.jobs.push({id:'jobX',name:'Peach',status:'active'});showView('jobs')"); await pg.wait_for_timeout(800)
        btn=pg.locator('button[onclick^="archiveJob"]').first
        print('archive btn svg:', await btn.locator('svg').count(), 'text:', (await btn.inner_text()).strip(), 'errors', errs[:2])
        await btn.screenshot(path='/tmp/arch.png')
        await b.close()
asyncio.run(main())
