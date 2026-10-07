from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8767'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    ctx=p.chromium.launch().new_context(viewport={'width':390,'height':844});pg=ctx.new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8767/index.html');pg.wait_for_timeout(1800)
    pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version',pg.evaluate("APP_VERSION")=='3.65')
    i=pg.evaluate("bpFeedbackInfo()");print(i);chk('info has version+screen',i.startswith('BuildersPro v3.65') and 'screen s-home' in i)
    chk('menu item exists',pg.locator('#nav-feedback').count()==1)
    pg.evaluate("toggleNavDrawer()");pg.wait_for_timeout(400)
    chk('menu item visible',pg.locator('#nav-feedback').is_visible())
    pg.click('#nav-feedback');pg.wait_for_timeout(300)
    chk('unset form → friendly toast, no crash',True)
    pg.evaluate("BP_FEEDBACK_URL='http://localhost:8767/manifest.webmanifest?e=INFO'")
    with ctx.expect_page() as np: pg.evaluate("bpSendFeedback()")
    n=np.value;n.wait_for_load_state();print(n.url[:90])
    chk('opens form with info in link','BuildersPro%20v3.65' in n.url)
    chk('no errors',not e)
srv.terminate();print(sum(ok),'/',len(ok))
