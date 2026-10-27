import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await (await b.new_context(viewport={'width':390,'height':844})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8799/index.html')
        await pg.wait_for_timeout(2000)
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        print("version:", await pg.evaluate("APP_VERSION"))

        await pg.evaluate("""(()=>{
            DB.jobs=[{id:'j1',name:'Shedwick',status:'Active',security:[]}];
            DB.rooms=[]; DB.expenses=[]; DB.contractors=[]; DB.invoices=[]; DB.permits=[]; DB.punchlist=[]; DB.photos=[];
            save(); renderAll(); openJobDetail('j1');
        })()""")
        await pg.wait_for_timeout(500)

        # --- Job Sections hamburger (bpHMenu) ---
        before = await pg.evaluate("""
            Array.from(document.querySelectorAll('#jd-sections-trigger .bp-hm-btn svg line')).map(l=>getComputedStyle(l).transform)
        """)
        await pg.evaluate("document.querySelector('#jd-sections-trigger .bp-hm-btn').click()")
        await pg.wait_for_timeout(300)
        after = await pg.evaluate("""
            Array.from(document.querySelectorAll('#jd-sections-trigger .bp-hm-btn svg line')).map(l=>getComputedStyle(l).transform)
        """)
        mid_opacity = await pg.evaluate("getComputedStyle(document.querySelectorAll('#jd-sections-trigger .bp-hm-btn svg line')[1]).opacity")
        print("bpHMenu line transforms before:", before)
        print("bpHMenu line transforms after (open):", after)
        print("bpHMenu middle line opacity when open:", mid_opacity)
        await pg.screenshot(path='/tmp/x_jobsections.png')
        await pg.evaluate("document.querySelector('#jd-sections-trigger .bp-hm-btn').click()")  # close
        await pg.wait_for_timeout(300)

        # --- Main dock hamburger (nav drawer) ---
        before2 = await pg.evaluate("""
            Array.from(document.querySelectorAll('#bp-dock-menu svg line')).map(l=>getComputedStyle(l).transform)
        """)
        await pg.evaluate("document.getElementById('bp-dock-menu').click()")
        await pg.wait_for_timeout(350)
        after2 = await pg.evaluate("""
            Array.from(document.querySelectorAll('#bp-dock-menu svg line')).map(l=>getComputedStyle(l).transform)
        """)
        drawer_open = await pg.evaluate("document.body.classList.contains('bp-drawer-open')")
        print("drawer open:", drawer_open)
        print("dock-menu line transforms before:", before2)
        print("dock-menu line transforms after (open):", after2)
        await pg.screenshot(path='/tmp/x_drawer.png')

        print("page errors:", errs)
        await b.close()

asyncio.run(main())
