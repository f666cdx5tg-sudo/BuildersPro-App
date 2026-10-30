"""v6.6.0 — Stan's Oct 30 list.
1. A trade left on from the job page: "7 open" still shows all 7 (trade set back to All); menu label = real trade.
2. Trades button is a hamburger (three lines).
3. Home "Open punch" tile → Punch, every open item.
4. Job heading: status beside the name; client, then address "street, City, ST"; contract; start date; no "BSP";
   Received / Balance amounts under their labels.
5. Documents: no pencil/trash on the card; slide left shows Edit + Delete; whole name shows.
Run from repo root: python3 test_v660_punch_job_docs.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8960
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',client:'Shelden Washington',address:'1536 N. Peach St',city:'Philadelphia',state:'Pennsylvania',zip:'19131',status:'Active',contract:45000,startDate:'2026-08-19'},
           {id:'j2',name:'Shedwick',client:'C',address:'9 Elm',status:'Active'}];
  DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1'},{id:'r2',jobId:'j1',name:'Bath',level:'Level 1'}];
  DB.punchlist=[]; var tr=['Plumbing','Electrical','Painting'];
  for (var i=0;i<12;i++) DB.punchlist.push({id:'p'+i,jobId:'j1',roomId:i<6?'r1':'r2',text:'Item '+i,trade:tr[i%3],done:i>=7,created:t});
  DB.documents=[{id:'d1',jobId:'j1',name:'Lease agreement for the second floor apartment unit B',category:'Other',fileSrc:'data:application/pdf;base64,JVBERi0=',fileType:'application/pdf',created:t}];
  DB.payments=[]; DB.invoices=[{id:'i1',jobId:'j1',amount:5000,status:'Paid',date:t.slice(0,10)}];
  try{bpSave()}catch(e){try{saveDB()}catch(e2){}} try{bpSetActiveJob('j1',true)}catch(e){} }"""
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width':402,'height':874}, is_mobile=True, has_touch=True)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()"); await pg.evaluate(SEED)
            SHOWN = "[].filter.call(document.querySelectorAll('#punch-body *'), function(e){ return !e.children.length && /^Item \\d+$/.test(e.textContent.trim()) && e.offsetParent; }).length"

            print('\n1. Punch: a trade left on from the job page')
            await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(600)
            await pg.evaluate("filterPunchCategory('Plumbing')"); await pg.wait_for_timeout(400)
            await pg.evaluate("showScreen('s-punch')"); await pg.wait_for_timeout(800)
            ok('7 open' in await pg.inner_text('#punch-count'), 'header says 7 open')
            lbl = await pg.evaluate("(document.querySelector('#s-punch .bp-trade-hm .bp-th-cur')||{}).textContent || ''")
            await pg.click('#punch-count .bp-pc.o'); await pg.wait_for_timeout(800)
            ok(await pg.evaluate(SHOWN) == 7, 'tapping "7 open" shows all 7 open items (%s)' % await pg.evaluate(SHOWN))
            ok(await pg.evaluate("bpPunchTradeNow()") == '', 'trade set back to All')
            await pg.click('#punch-count .bp-pc.d'); await pg.wait_for_timeout(800)
            ok(await pg.evaluate(SHOWN) == 5, 'tapping "5 done" shows the 5 done items')
            await pg.click('#punch-count .bp-pc.o'); await pg.wait_for_timeout(600)

            print('\n2. Trades menu')
            ok(await pg.evaluate("!!document.querySelector('#s-punch .bp-trade-hm .bp-hm-btn .bp-burger-ic') && !document.querySelector('#s-punch .bp-trade-hm .bp-hm-btn .bp-dots')"), 'trades button is a hamburger, not •••')
            await pg.evaluate("document.querySelector('#s-punch .bp-trade-hm .bp-hm-btn').click()"); await pg.wait_for_timeout(300)
            items = await pg.evaluate("[].map.call(document.querySelectorAll('.bp-hm-float .bp-hm-it'), function(i){ return i.textContent.trim(); })")
            ok(not any(ch for it in items for ch in it if ord(ch) > 0x2500 and ch != '✓'), 'trade list has no emoji %s' % items)
            pick = await pg.evaluate("(function(){ var it=[].find.call(document.querySelectorAll('.bp-hm-float .bp-hm-it'), function(i){ return /Electrical/.test(i.textContent); }); if(!it) return false; it.click(); return true; })()"); await pg.wait_for_timeout(600)
            ok(pick and await pg.evaluate("bpPunchTradeNow()") == 'Electrical', 'picking Electrical sets Electrical %s' % items)
            ok('Electrical' in await pg.evaluate("document.querySelector('#s-punch .bp-trade-hm .bp-th-cur').textContent"), 'label says Trade Electrical')
            await pg.evaluate("document.querySelector('#s-punch .bp-trade-hm .bp-hm-btn').click()"); await pg.wait_for_timeout(300)
            await pg.evaluate("(function(){ var it=[].find.call(document.querySelectorAll('.bp-hm-float .bp-hm-it'), function(i){ return /Electrical/.test(i.textContent); }); it && it.click(); })()"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("bpPunchTradeNow()") == 'Electrical', 'picking the same trade again keeps it (no hidden toggle-off)')

            print('\n3. Home Open punch tile')
            await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(800)
            await pg.evaluate("document.querySelector('[data-tile=\"punch\"]').click()"); await pg.wait_for_timeout(900)
            ok(await pg.evaluate("document.querySelector('.screen.active').id") == 's-punch', 'opens Punch')
            ok(await pg.evaluate(SHOWN) == 7 and await pg.evaluate("bpPunchTradeNow()") == '', 'shows all 7 open items, trade All')

            print('\n4. Job heading')
            await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(800)
            name = await pg.evaluate("(function(){ var n=document.getElementById('jd-name'), s=n.querySelector('.bp-jd-st'); return { t:n.textContent, st: s && s.textContent, same: s && Math.abs(s.getBoundingClientRect().top - n.firstChild.getBoundingClientRect().top) < 12 }; })()")
            ok(name['st'] == 'Active' and name['same'], 'green Active sits beside the name %s' % name)
            rows = await pg.evaluate("[].map.call(document.querySelectorAll('#jd-meta .bp-jd-row, #jd-info .bp-jd-row'), function(r){ return r.textContent.trim(); })")
            ok(rows == ['Shelden Washington', '1536 N. Peach St, Philadelphia, PA', 'Contract $45,000', 'Start 08/19/2026'], 'client, address (City, ST), contract, start — in that order %s' % rows)
            ok(not await pg.evaluate("[].some.call(document.querySelectorAll('#s-job-detail span'), function(s){ return s.textContent === 'BSP'; })"), 'no BSP label')
            al = await pg.evaluate("[].map.call(document.querySelectorAll('#jd-progress-toggles .bp-money-cell'), function(c){ var l=c.querySelector('span').getBoundingClientRect(), b=c.querySelector('b').getBoundingClientRect(); return [Math.round(l.left), Math.round(b.left), b.top > l.top]; })")
            ok(len(al) == 2 and all(abs(a[0]-a[1]) <= 2 and a[2] for a in al), 'Received / Balance amounts sit under their labels, lined up left %s' % al)

            print('\n5. Documents')
            await pg.evaluate("var s=document.getElementById('jd-documents-section'); s && s.scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
            vis = await pg.evaluate("[].filter.call(document.querySelectorAll('#jd-documents-section .bp-doc-edit-btn, #jd-documents-section .bp-doc-del-btn'), function(b){ return b.offsetParent; }).length")
            ok(vis == 0, 'no pencil or trash on the card')
            nm = await pg.evaluate("(function(){ var r=document.querySelector('.bp-doc-row'); var n=[].find.call(r.querySelectorAll('div'), function(d){ return /Lease agreement/.test(d.textContent) && !d.children.length; }); return n ? n.scrollWidth <= n.clientWidth + 1 : null; })()")
            ok(nm, 'whole document name shows (no "…")')
            row = await pg.query_selector('.bp-doc-row'); bb = await row.bounding_box()
            cdp = await ctx.new_cdp_session(pg)
            y = bb['y'] + bb['height']/2; x0 = bb['x'] + bb['width'] - 30
            await cdp.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x0,'y':y}]})
            for k in range(1, 11): await cdp.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x0 - k*20,'y':y}]})
            await cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]}); await pg.wait_for_timeout(400)
            acts = await pg.evaluate("(function(){ var a=document.querySelector('.bp-doc-swipe .bp-doc-acts'); return [].map.call(a.querySelectorAll('button'), function(b){ var r=b.getBoundingClientRect(), e=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return [b.textContent.trim(), !!(e && b.contains(e))]; }); })()")
            ok(acts == [['Edit', True], ['Delete', True]], 'slide left shows Edit and Delete %s' % acts)
            await pg.evaluate("(function(){ var b=[].find.call(document.querySelectorAll('.bp-doc-acts button'), function(x){ return /Edit/.test(x.textContent); }); b.click(); })()"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("!!document.getElementById('bpde-name') || !!document.querySelector('[id^=bp-edit-doc], #bp-doc-edit')"), 'Edit opens the document editor')
            ok(not errs, 'no page errors %s' % errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
