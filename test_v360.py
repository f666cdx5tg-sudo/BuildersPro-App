from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8761'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
with sync_playwright() as p:
    pg=p.chromium.launch().new_page(viewport={'width':390,'height':844});e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8761/index.html');pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('bp-lock')?.remove();DB.jobs.push({id:'t',name:'N Peach',status:'Active',startDate:'2026-08-19'});openJobDetail('t')");pg.wait_for_timeout(300)
    r=pg.evaluate("[...document.querySelectorAll('#jd-progress-toggles label')].map(l=>l.textContent.trim())");print(r)
    ok=r[0]=='Started' and r[1].startswith('Done') and '—' in r[1] and 'APP' or True
    a=r[0]=='Started'; b=pg.evaluate("document.getElementById('jd-info').textContent.includes('08/19/2026')")
    print('started no date',a,'heading has date',b,'errs',e,'ver',pg.evaluate("APP_VERSION"))
    pg.evaluate("toggleJobStarted('t')");pg.wait_for_timeout(200)
    print(pg.evaluate("[...document.querySelectorAll('#jd-progress-toggles label')].map(l=>l.textContent.trim())"))
srv.terminate()
