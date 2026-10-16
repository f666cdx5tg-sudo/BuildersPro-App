from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8779'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
SEED="DB.jobs=[{id:'j1',name:'J',status:'Active'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1'}];DB.punchlist=[{id:'a',jobId:'j1',roomId:'r1',text:'Open one',done:false},{id:'b',jobId:'j1',roomId:'r1',text:'Done one',done:true}];"
ROUND="(function(sel){var e=document.querySelector(sel);if(!e)return 'missing';var r=e.getBoundingClientRect(),c=getComputedStyle(e);return Math.abs(r.width-r.height)<1&&parseFloat(c.borderTopLeftRadius)>=r.width/2-1&&e.querySelectorAll('svg.bp-dots circle').length===3&&e.querySelectorAll('svg line').length===0;})"
try:
  with sync_playwright() as p:
    b=p.chromium.launch()
    for vw,label in ((390,'phone'),(834,'ipad')):
        pg=b.new_context(viewport={'width':vw,'height':844 if vw<500 else 1194}).new_page();e=[];pg.on('pageerror',lambda x:e.append(str(x)))
        pg.goto('http://localhost:8779/index.html');pg.wait_for_timeout(2200);pg.evaluate("document.getElementById('bp-lock')?.remove()")
        chk(label+' version 4.25',pg.evaluate("APP_VERSION")=='4.25')
        chk(label+' dock Menu button is a round ••• (3 dots, no lines)',pg.evaluate(ROUND+"('#bp-dock-menu')") is True)
        pg.evaluate(SEED+"window._bpPunchJob='j1';window._bpClFilter.show='open';showScreen('s-punch');bpRenderPunch();bpOpenPunchArea('r1')")
        pg.wait_for_timeout(700)
        chk(label+' Status/Space option buttons are round •••',pg.evaluate(ROUND+"('#bp-clf-punch .bp-pm .bp-hm-btn')") is True)
        n=pg.evaluate("document.querySelectorAll('.bp-hm-btn').length")
        chk(label+' every option button has dots, none has 3 lines',n>=1 and pg.evaluate("[].every.call(document.querySelectorAll('.bp-hm-btn'),function(b){return b.querySelectorAll('svg.bp-dots circle').length===3&&b.querySelectorAll('line').length===0})"))
        pg.locator('#bp-clf-punch .bp-pm').first.locator('.bp-hm-btn').click();pg.wait_for_timeout(250)
        chk(label+' tapping ••• still opens the option menu',pg.locator('#bp-clf-punch .bp-pm').first.locator('.bp-hm-it').count()==2 and pg.locator('.bp-hm.open').count()==1)
        pg.screenshot(path='/tmp/v425_%s_menu.png'%label)
        pg.locator('#bp-clf-punch .bp-pm').first.locator('.bp-hm-it',has_text='Complete').click();pg.wait_for_timeout(400)
        chk(label+' choosing an option still works',('Done one' in pg.locator('#pn-groups').inner_text()))
        pg.evaluate("toggleNavDrawer()");pg.wait_for_timeout(400)
        chk(label+' side menu still opens',pg.evaluate("document.body.classList.contains('bp-drawer-open')"))
        chk(label+' no page errors',len(e)==0)
        if e: print(e)
    b.close()
finally:
    srv.terminate()
print('ALL PASS' if all(ok) else 'SOME FAILED',sum(ok),'/',len(ok))
