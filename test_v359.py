from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8760'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
try:
  with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={'width':390,'height':844});errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8760/index.html');pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{document.getElementById('bp-lock')?.remove();
    DB.jobs.push({id:'tj',name:'Smith Kitchen',address:'12 Oak',client:'Pat',status:'Active',contract:50000});
    DB.rooms.push({id:'r1',jobId:'tj',name:'Kitchen',type:'Kitchen',level:'Level 2'},{id:'r2',jobId:'tj',name:'Boiler Room',type:'Basement',level:'Basement'},{id:'r3',jobId:'tj',name:'Bath',type:'Bathroom',level:'Level 1'},{id:'r4',jobId:'tj',name:'Mystery',type:'Other'});
    DB.expenses.push({id:'e1',jobId:'tj',amount:120,desc:'Pipe',vendor:'Ferg',date:'2026-10-01',category:'Materials'});
    DB.contractors.push({id:'c1',jobId:'tj',name:'Joe',trade:'Plumber',value:3000});
    DB.invoices.push({id:'i1',jobId:'tj',desc:'Deposit',amount:5000,status:'Paid',date:'2026-10-01'});
    DB.permits.push({id:'p1',jobId:'tj',permitNumber:'P-1',type:'Plumbing',status:'Approved'});
    DB.reports.push({id:'d1',jobId:'tj',date:'2026-10-02',dprNumber:1});
    openJobDetail('tj')}""");pg.wait_for_timeout(500)
    keys=pg.evaluate("[...document.querySelectorAll('#jd-stack .bp-acc')].map(a=>a.dataset.k)")
    print(keys)
    chk('8 sections in order',keys==['spaces','finance','expenses','contractors','invoices','permits','reports','photos'])
    lv=pg.evaluate("[...document.querySelectorAll('#jd-stack .bp-lvl')].map(x=>x.textContent)")
    print(lv);chk('levels ordered',lv==['Basement','Level 1','Level 2','Level not set'])
    cts=pg.evaluate("[...document.querySelectorAll('#jd-stack .bp-acc-h .ct')].map(x=>x.textContent)");print(cts)
    chk('counts',cts[0]=='4' and cts[2]=='1' and cts[3]=='1' and cts[4]=='1')
    chk('spaces open by default',pg.evaluate("document.querySelector('.bp-acc[data-k=spaces]').classList.contains('open')"))
    chk('expenses collapsed',not pg.evaluate("document.querySelector('.bp-acc[data-k=expenses]').classList.contains('open')"))
    pg.click('.bp-acc[data-k=expenses] .bp-acc-h');chk('tap opens',pg.evaluate("document.querySelector('.bp-acc[data-k=expenses]').classList.contains('open')"))
    chk('expense row visible',pg.locator('.bp-acc[data-k=expenses] >> text=Pipe').first.is_visible())
    pg.click('.bp-acc[data-k=finance] .bp-acc-h');chk('finance shows balance',pg.locator('.bp-acc[data-k=finance] >> text=Balance owed').is_visible())
    hh=pg.evaluate("document.querySelector('.bp-acc-h').getBoundingClientRect().height");chk('48px header',hh>=44)
    pg.evaluate("renderJobDetail('tj')");pg.wait_for_timeout(200)
    chk('re-render keeps one stack, open state',pg.locator('#jd-stack').count()==1 and pg.locator('#jd-stack .bp-acc').count()==8 and pg.evaluate("document.querySelector('.bp-acc[data-k=expenses]').classList.contains('open')"))
    chk('single jd-photos',pg.locator('#jd-photos').count()==1)
    pg.click('.bp-acc[data-k=photos] .bp-acc-h');chk('photos inside stack',pg.evaluate("!!document.querySelector('#jd-stack #jd-photos')"))
    pg.click('.bp-acc[data-k=finance] button:has-text("Open Finance")');pg.wait_for_timeout(300)
    chk('finance opens filtered',pg.evaluate("document.getElementById('s-finance').classList.contains('active') && document.getElementById('finance-job-filter').value==='tj'"))
    pg.evaluate("openJobDetail('tj')");pg.wait_for_timeout(300)
    pg.screenshot(path='/tmp/claude-0/v359.png',full_page=False)
    chk('no page errors',not errs)
    if errs:print(errs)
finally: srv.terminate()
print(sum(ok),'/',len(ok))
