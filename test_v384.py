import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width':390,'height':844})
        await page.goto('http://localhost:8799/index.html')
        await page.evaluate("document.getElementById('bp-lock')?.remove()")
        await page.wait_for_timeout(300)

        # seed a job
        await page.evaluate("""
        () => {
          DB.jobs = DB.jobs || [];
          var j = {id:'jobX', name:'Test Job', security:[{id:'s1'}]};
          DB.jobs.push(j);
          DB.rooms = DB.rooms || [];
          DB.rooms.push({id:'r1', jobId:'jobX', name:'Kitchen'});
          window.showScreen && window.showScreen('s-job-detail');
          window.renderJobDetail && window.renderJobDetail('jobX');
        }
        """)
        await page.wait_for_timeout(500)

        # Check initial state: only spaces (default open) visible, others hidden
        visible_accs = await page.evaluate("""
        () => {
          var out = {};
          document.querySelectorAll('#jd-stack .bp-acc').forEach(function(acc){
            var k = acc.getAttribute('data-k');
            out[k] = getComputedStyle(acc).display !== 'none';
          });
          var sec = document.getElementById('jd-security-section');
          out['security'] = sec ? getComputedStyle(sec).display !== 'none' : null;
          return out;
        }
        """)
        print("Initial visibility:", visible_accs)

        # Open the Job Sections menu and click "Finance"
        await page.evaluate("""
        () => {
          var trig = document.getElementById('jd-sections-trigger');
          var btn = trig.querySelector('.bp-hm-btn');
          btn.click();
        }
        """)
        await page.wait_for_timeout(200)
        await page.evaluate("""
        () => { window.bpOpenJobSection('finance','jobX'); }
        """)
        await page.wait_for_timeout(300)

        visible_after = await page.evaluate("""
        () => {
          var out = {};
          document.querySelectorAll('#jd-stack .bp-acc').forEach(function(acc){
            var k = acc.getAttribute('data-k');
            out[k] = getComputedStyle(acc).display !== 'none';
          });
          var sec = document.getElementById('jd-security-section');
          out['security'] = sec ? getComputedStyle(sec).display !== 'none' : null;
          return out;
        }
        """)
        print("After opening Finance via menu:", visible_after)

        # count how many visible = true
        true_count = sum(1 for v in visible_after.values() if v)
        print("Total visible sections:", true_count)

        await browser.close()

asyncio.run(main())
