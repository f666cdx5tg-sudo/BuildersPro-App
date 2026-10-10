from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8769'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    pg=p.chromium.launch().new_page(viewport={'width':390,'height':844});e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8769/index.html');pg.wait_for_timeout(1800)
    pg.evaluate("document.getElementById('bp-lock')?.remove();showScreen('s-home')")
    box=lambda: pg.evaluate("(()=>{var r=document.getElementById('info-time').getBoundingClientRect();return [Math.round(r.left*10)/10,Math.round(r.right*10)/10,Math.round(r.top*10)/10,Math.round(r.width*10)/10]})()")
    fs=pg.evaluate("parseFloat(getComputedStyle(document.getElementById('info-time')).fontSize)")
    chk('font >= 28px (was 18)',fs>=28)
    seen=set()
    for t in ['9:59 AM','10:00 AM','11:11 PM','1:08 PM','12:30 AM']:
        pg.evaluate("t=>{document.getElementById('info-time').textContent=t}",t);seen.add(tuple(box()[1:3]))
    print(seen);chk('right edge + top identical for every time',len(seen)==1)
    w=set()
    for t in ['9:59 AM','10:00 AM','11:11 PM']:
        pg.evaluate("t=>{document.getElementById('info-time').textContent=t}",t);w.add(box()[3])
    chk('fixed width slot',len(w)==1)
    pg.evaluate("document.getElementById('info-loc-text').textContent='1536 N. Peach Street, Philadelphia, PA 19131 United States'")
    chk('long address does not push it',tuple(box()[1:3]) in seen)
    pg.evaluate("document.querySelector('#s-home').scrollTop=400;window.scrollTo(0,400)");pg.wait_for_timeout(200)
    chk('stays put when scrolled (sticky)',box()[2]<120)
    pg.screenshot(path='/tmp/claude-0/v402.png',clip={'x':0,'y':0,'width':390,'height':260})
    chk('no errors',not e)
srv.terminate();print(sum(ok),'/',len(ok))
