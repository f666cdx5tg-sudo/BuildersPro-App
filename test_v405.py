from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8772'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    pg=p.chromium.launch().new_page(viewport={'width':390,'height':844});e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8772/index.html');pg.wait_for_timeout(1800)
    pg.evaluate("document.getElementById('bp-lock')?.remove();showScreen('s-home')")
    t=pg.inner_text('#home-greeting');print(t);chk('no name → welcome back',t.endswith('welcome back'))
    pg.evaluate("_userName='Stan Robinson';updateGreeting()")
    t=pg.inner_text('#home-greeting');print(t);chk('first name only',t.endswith(', Stan'))
    chk('weight 400',pg.evaluate("getComputedStyle(document.getElementById('home-greeting')).fontWeight")=='400')
    h=pg.evaluate("document.getElementById('home-greeting').getBoundingClientRect().height");print(h);chk('one line',h<32)
    pg.evaluate("_userName='Bartholomew';document.getElementById('home-greeting').textContent='Good Afternoon, Bartholomew'")
    h2=pg.evaluate("document.getElementById('home-greeting').getBoundingClientRect().height");print('long',h2)
    pg.evaluate("_userName='Stan Robinson';updateGreeting()")
    pg.screenshot(path='/tmp/claude-0/v405.png',clip={'x':0,'y':0,'width':390,'height':160})
    chk('no errors',not e)
srv.terminate();print(sum(ok),'/',len(ok))
