from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8777'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_context(viewport={'width':390,'height':844}).new_page();e=[];pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8777/index.html');pg.wait_for_timeout(2200);pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version',pg.evaluate("APP_VERSION")=='4.23')
    pg.evaluate("DB.jobs=[{id:'j1',name:'J',status:'Active'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1'}];DB.punchlist=[{id:'a',jobId:'j1',roomId:'r1',text:'Done one',done:true},{id:'b',jobId:'j1',roomId:'r1',text:'Open one',done:false}];(window.bpSave||save)();openRoomDetail('r1')")
    pg.wait_for_timeout(600)
    t=pg.locator('#s-room-detail').inner_text();chk('shows 1 left',('50%' in t) and ('1 left' in t))
    pg.locator('text=1 left').click();pg.wait_for_timeout(800)
    t=pg.locator('#punch-body').inner_text();chk('opens punch list with only the open item',('Open one' in t) and ('Done one' not in t))
    chk('no JS errors',not e);print(e)
print(sum(ok),'/',len(ok));srv.kill()
