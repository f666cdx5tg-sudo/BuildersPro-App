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
            DB.jobs=[{id:'j1',name:'Shedwick',status:'Active'}];
            DB.rooms=[{id:'r1',name:'Yard / Grading',type:'Exterior',space:'Exterior',jobId:'j1'}];
            DB.punchlist=[]; DB.photos=[]; save(); renderAll(); openJobDetail('j1');
        })()""")
        await pg.wait_for_timeout(400)

        # Case 1: job-level "Add Item" (no room yet) -> Area picker should show, context = job only
        await pg.evaluate("openAddNote('j1')")
        await pg.wait_for_timeout(200)
        ctx1 = await pg.evaluate("document.getElementById('an-context').textContent")
        area_visible1 = await pg.evaluate("getComputedStyle(document.getElementById('an-room-wrap')).display") != 'none'
        job_visible1 = await pg.evaluate("getComputedStyle(document.getElementById('an-job')).display") != 'none'
        print("Case1 (job-level) context:", repr(ctx1), "| area shown:", area_visible1, "| job select visible:", job_visible1)
        await pg.evaluate("closeSheet('sheet-add-note')")

        # Case 2: room-level "+ Item" -> both Job and Area hidden, context = job + area
        await pg.evaluate("openAddNote('j1','r1')")
        await pg.wait_for_timeout(200)
        ctx2 = await pg.evaluate("document.getElementById('an-context').textContent")
        area_visible2 = await pg.evaluate("getComputedStyle(document.getElementById('an-room-wrap')).display") != 'none'
        job_visible2 = await pg.evaluate("getComputedStyle(document.getElementById('an-job')).display") != 'none'
        print("Case2 (room-level) context:", repr(ctx2), "| area shown:", area_visible2, "| job select visible:", job_visible2)

        # Fill and save, confirm item saved with correct jobId/roomId despite hidden fields
        await pg.fill("#an-text", "Check sprinkler heads")
        await pg.evaluate("saveNote()")
        await pg.wait_for_timeout(300)
        item = await pg.evaluate("DB.punchlist[0]")
        print("Saved item jobId/roomId/text:", item['jobId'], item['roomId'], item['text'])

        print("page errors:", errs)
        await b.close()

asyncio.run(main())
