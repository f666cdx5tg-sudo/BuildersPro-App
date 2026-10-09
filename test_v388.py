import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto("http://localhost:8799/desktop.html"); await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(800)
        print('default zoom', await pg.evaluate("document.body.style.zoom"), 'label', await pg.evaluate("document.getElementById('bp-size-lbl').textContent"))
        await pg.screenshot(path='/tmp/d100.png')
        await pg.click('#bp-size-btn'); await pg.wait_for_timeout(300)
        print('panel open', await pg.evaluate("document.getElementById('bp-gs-wrap').classList.contains('open')"))
        await pg.click('.bp-gp[data-pct="145"]'); await pg.wait_for_timeout(400)
        st=await pg.evaluate("({z:document.body.style.zoom,sv:localStorage.getItem('bp_zoom_d'),val:document.querySelector('[data-gv]').textContent,sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,bh:document.body.getBoundingClientRect().height,ih:innerHeight})")
        print('after 145:', st)
        await pg.screenshot(path='/tmp/d145.png')
        await pg.click('.bp-gb[data-gd="1"]'); await pg.wait_for_timeout(200)
        print('after A+:', await pg.evaluate("document.querySelector('[data-gv]').textContent"))
        await pg.click('#bp-gs-done'); await pg.reload(); await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(600)
        print('persisted zoom', await pg.evaluate("document.body.style.zoom"), 'errors', errs[:3])
        await b.close()
asyncio.run(main())
