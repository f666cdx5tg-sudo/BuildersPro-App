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
            DB.jobs=[{id:'j1',name:'Shedwick',status:'Active',
              security:[{id:'s1',kind:'other',label:'Gate code',secret:'1234'},
                        {id:'s2',kind:'other',label:'Lockbox',secret:'5678'},
                        {id:'s3',kind:'other',label:'Alarm',secret:'9999'}]}];
            DB.rooms=[];
            for (let i=0;i<20;i++) DB.rooms.push({id:'r'+i,name:'Room '+i,type:'Bedroom',space:'Interior',jobId:'j1'});
            DB.expenses=[]; DB.contractors=[]; DB.invoices=[]; DB.permits=[]; DB.punchlist=[]; DB.photos=[];
            save(); renderAll(); openJobDetail('j1');
        })()""")
        await pg.wait_for_timeout(500)

        # 1. The individual Security card and accordion stack should be hidden by default
        sec_visible = await pg.evaluate("!!(document.getElementById('jd-security-section')?.offsetHeight)")
        stack_visible = await pg.evaluate("!!(document.getElementById('jd-stack')?.offsetHeight)")
        print("Security card visible by default:", sec_visible)
        print("Accordion stack visible by default:", stack_visible)

        # 2. The single trigger row should be visible, right after the quick actions
        trig = await pg.evaluate("""(() => {
            var t = document.getElementById('jd-sections-trigger');
            return t ? { visible: !!t.offsetHeight, text: t.querySelector('span').textContent } : null;
        })()""")
        print("Trigger row:", trig)

        # 3. Open the hamburger and inspect menu items (labels should carry counts)
        await pg.evaluate("document.querySelector('#jd-sections-trigger .bp-hm-btn').click()")
        await pg.wait_for_timeout(150)
        labels = await pg.evaluate("""
            Array.from(document.querySelectorAll('#jd-sections-trigger .bp-hm-it')).map(b=>b.textContent.trim())
        """)
        print("Menu items:", labels)

        # 4. Click "Spaces" item, confirm it reveals + opens + scrolls
        spaces_btn = await pg.query_selector("#jd-sections-trigger .bp-hm-it:has-text('Spaces')")
        await spaces_btn.click()
        await pg.wait_for_timeout(300)
        stack_visible_after = await pg.evaluate("!!(document.getElementById('jd-stack')?.offsetHeight)")
        spaces_open = await pg.evaluate("document.querySelector('#jd-stack .bp-acc[data-k=\"spaces\"]').classList.contains('open')")
        print("Stack visible after picking Spaces:", stack_visible_after, "| spaces accordion open:", spaces_open)

        # Security section should also now be visible (collapsed class removed) even though not opened
        sec_visible_after = await pg.evaluate("!!(document.getElementById('jd-security-section')?.offsetHeight)")
        print("Security card visible after revealing (not necessarily open):", sec_visible_after)

        print("page errors:", errs)
        await b.close()

asyncio.run(main())
