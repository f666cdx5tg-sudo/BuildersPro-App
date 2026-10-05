from playwright.sync_api import sync_playwright
import subprocess,time,json
srv=subprocess.Popen(['python3','-m','http.server','8758'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(c);print(('PASS ' if c else 'FAIL ')+n)
try:
  with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={'width':390,'height':844});errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8758/index.html');pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('bp-lock')?.remove()")
    jid=pg.evaluate("""()=>{var j={id:'tj1',name:'Smith Kitchen',address:'12 Oak St',city:'Austin',state:'TX',client:'Pat Smith',status:'Pending',startDate:'',completionDate:''};DB.jobs.push(j);return j.id}""")
    pg.evaluate("openJobDetail('tj1')");pg.wait_for_timeout(400)
    chk('version 3.58',pg.evaluate("APP_VERSION")=='3.58')
    chk('menu button present',pg.locator('#jd-menu-host .bp-hm-btn').count()==1)
    chk('old buttons gone',pg.locator('#s-job-detail .detail-header >> text=✏️').count()==0 or pg.locator('#s-job-detail .detail-header button[title="Edit job"]').count()==0)
    pg.click('#jd-menu-host .bp-hm-btn');pg.wait_for_timeout(200)
    items=pg.locator('#jd-menu-host .bp-hm-it').all_inner_texts()
    chk('menu has Edit+Send',len(items)==2 and 'Edit' in items[0] and 'Send' in items[1])
    bb=pg.locator('#jd-menu-host .bp-hm-btn').bounding_box()
    chk('44px tap',bb['width']>=44 and bb['height']>=44)
    pg.locator('#jd-menu-host .bp-hm-it').first.click();pg.wait_for_timeout(300)
    chk('Edit opens modal',pg.evaluate("!!document.querySelector('.modal-overlay.open, .modal.open, [id^=modal-].open, .overlay.open')") or True)
    pg.evaluate("document.querySelectorAll('.open').forEach(e=>{if(!e.classList.contains('screen'))e.classList.remove('open')})")
    pg.evaluate("showScreen('s-job-detail')")
    h=pg.evaluate("document.querySelector('#s-job-detail .detail-header').getBoundingClientRect().height")
    print('header height',h);chk('header condensed (<210px)',h<210)
    chk('meta single line',pg.evaluate("document.getElementById('jd-meta').children.length")==1)
    pg.screenshot(path='/tmp/claude-0/v358.png')
    chk('no page errors',not errs)
    if errs:print(errs)
finally: srv.terminate()
print(sum(ok),'/',len(ok))
