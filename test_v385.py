import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width':390,'height':844})
        await page.goto('http://localhost:8799/index.html')
        await page.evaluate("document.getElementById('bp-lock')?.remove()")
        await page.wait_for_timeout(300)
        await page.evaluate("""
        () => {
          DB.jobs = DB.jobs || [];
          var j = {id:'jobX', name:'Shedwick', security:[{id:'s1'}]};
          DB.jobs.push(j);
          window.showScreen && window.showScreen('s-job-detail');
          window.renderJobDetail && window.renderJobDetail('jobX');
        }
        """)
        await page.wait_for_timeout(400)

        # check blend-in button styling
        btn_style = await page.evaluate("""
        () => {
          var btn = document.querySelector('#jd-sections-trigger .bp-hm-btn');
          var cs = getComputedStyle(btn);
          return { bg: cs.backgroundColor, border: cs.borderStyle };
        }
        """)
        print("Button style (should be transparent/none):", btn_style)

        await page.screenshot(path='/tmp/v385_default.png')

        # open Finance via menu -> should go full page
        await page.evaluate("window.bpOpenJobSection('finance','jobX')")
        await page.wait_for_timeout(300)
        await page.screenshot(path='/tmp/v385_finance_fullpage.png')

        state = await page.evaluate("""
        () => {
          var out = {};
          document.querySelectorAll('#s-job-detail > *').forEach(function(c){
            out[(c.id||c.className||c.tagName)] = getComputedStyle(c).display;
          });
          return out;
        }
        """)
        print("Children display state (full page):", state)

        label = await page.evaluate("document.getElementById('jd-focus-label').textContent")
        print("Focus bar label:", label)

        # tap back
        await page.evaluate("window.bpCloseSectionFocus()")
        await page.wait_for_timeout(200)
        await page.screenshot(path='/tmp/v385_after_back.png')
        state2 = await page.evaluate("""
        () => {
          var out = {};
          document.querySelectorAll('#s-job-detail > *').forEach(function(c){
            out[(c.id||c.className||c.tagName)] = getComputedStyle(c).display;
          });
          return out;
        }
        """)
        print("Children display state (after back):", state2)

        await browser.close()

asyncio.run(main())
