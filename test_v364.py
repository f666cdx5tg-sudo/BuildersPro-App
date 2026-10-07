from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8765'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(viewport={'width':390,'height':844});pg=ctx.new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8765/index.html');pg.wait_for_timeout(2500)
    chk('version',pg.evaluate("APP_VERSION")=='3.64')
    pg.evaluate("document.getElementById('bp-lock')?.remove();DB.jobs.length||DB.jobs.push({id:'tj',name:'Smith',status:'Active'});localStorage.removeItem('bp_icloud_last');localStorage.removeItem('bp_backup_snooze');showScreen('s-home');bpPaintBackupNag()")
    pg.wait_for_timeout(300)
    chk('nag shows when never backed up',pg.locator('#bp-backup-nag').count()==1 and 'never' in pg.inner_text('#bp-backup-nag'))
    pg.evaluate("localStorage.setItem('bp_icloud_last',new Date().toISOString());bpPaintBackupNag()")
    chk('nag hides after backup',pg.locator('#bp-backup-nag').count()==0)
    pg.evaluate("localStorage.setItem('bp_icloud_last',new Date(Date.now()-9*864e5).toISOString());bpPaintBackupNag()")
    chk('nag shows at 9 days',pg.locator('#bp-backup-nag').count()==1 and '9 days' in pg.inner_text('#bp-backup-nag'))
    pg.click('#bp-backup-nag [aria-label^=Remind]');pg.wait_for_timeout(200)
    chk('snooze hides',pg.locator('#bp-backup-nag').count()==0)
    sw=pg.evaluate("navigator.serviceWorker.ready.then(r=>!!r.active)")
    chk('service worker active',sw)
    pg.reload();pg.wait_for_timeout(1500)
    chk('page controlled by SW',pg.evaluate("!!navigator.serviceWorker.controller"))
    ctx.set_offline(True)
    pg2=ctx.new_page();
    try:
        pg2.goto('http://localhost:8765/index.html',timeout=8000);pg2.wait_for_timeout(1500)
        chk('opens OFFLINE',pg2.evaluate("typeof APP_VERSION!=='undefined' && APP_VERSION")=='3.64')
    except Exception as ex: chk('opens OFFLINE '+str(ex)[:60],False)
    chk('no page errors',not e);print(e)
srv.terminate();print(sum(ok),'/',len(ok))
