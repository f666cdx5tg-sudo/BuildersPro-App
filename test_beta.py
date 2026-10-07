from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8766'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(viewport={'width':390,'height':844});pg=ctx.new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8766/index.html');pg.wait_for_timeout(2000)
    pg.evaluate("document.getElementById('bp-lock')?.remove();DB.jobs.push({id:'main1',name:'MAIN JOB',status:'Active'});save();localStorage.setItem('bp_active_job','main1')");pg.wait_for_timeout(800)
    pg2=ctx.new_page();pg2.on('pageerror',lambda x:e.append(str(x)))
    pg2.goto('http://localhost:8766/beta/index.html');pg2.wait_for_timeout(2500)
    pg2.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('beta title',pg2.title()=='BuildersPro Beta')
    chk('beta has none of main data',pg2.evaluate("!(DB.jobs||[]).some(j=>j.id==='main1')"))
    chk('beta localStorage isolated',pg2.evaluate("localStorage.getItem('bp_active_job')")!='main1')
    pg2.evaluate("DB.jobs.push({id:'beta1',name:'BETA JOB',status:'Active'});save();localStorage.setItem('bp_active_job','beta1')");pg2.wait_for_timeout(800)
    pg.reload();pg.wait_for_timeout(2500)
    chk('main untouched by beta',pg.evaluate("!(DB.jobs||[]).some(j=>j.id==='beta1') && (DB.jobs||[]).some(j=>j.id==='main1')"))
    chk('main active job intact',pg.evaluate("localStorage.getItem('bp_active_job')")=='main1')
    dbs=pg2.evaluate("indexedDB.databases().then(d=>d.map(x=>x.name).sort())");print(dbs)
    chk('two separate databases',dbs==['bp_idb','bp_idb_beta'])
    chk('BETA ribbon',pg2.evaluate("getComputedStyle(document.body,'::after').content")=='"BETA"')
    pg2.reload();pg2.wait_for_timeout(2000)
    chk('beta persists its own data',pg2.evaluate("(DB.jobs||[]).some(j=>j.id==='beta1')"))
    chk('beta SW own scope',pg2.evaluate("navigator.serviceWorker.getRegistration('/beta/').then(r=>!!r&&r.scope.endsWith('/beta/'))"))
    chk('no page errors',not e);print(e)
srv.terminate();print(sum(ok),'/',len(ok))
