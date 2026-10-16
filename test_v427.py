from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8782'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
INJECT="""(function(){var h=document.createElement('div');h.id='t427';h.style.cssText='position:fixed;top:60px;left:10px;z-index:99999;background:#111;color:#fff;padding:12px;display:flex;gap:14px;font-size:22px';
h.innerHTML='<button id="tl">☑️ Checklist</button><button id="ta">📎 Attach</button><button id="te">✏️ Edit</button>';document.body.appendChild(h);})()"""
FIRST="(function(sel){var e=document.querySelector(sel);return e&&e.querySelector('svg')})"
try:
  with sync_playwright() as p:
    b=p.chromium.launch()
    for page,label in (('index.html','field'),('desktop.html','desktop')):
        pg=b.new_context(viewport={'width':1000 if label=='desktop' else 390,'height':800}).new_page();e=[];pg.on('pageerror',lambda x:e.append(str(x)))
        pg.goto('http://localhost:8782/'+page);pg.wait_for_timeout(2500);pg.evaluate("document.getElementById('bp-lock')?.remove()")
        chk(label+' version 4.27',pg.evaluate("APP_VERSION")=='4.27')
        pg.evaluate(INJECT);pg.wait_for_timeout(1200)
        chk(label+' checklist icon (filled check disc + empty ring + 2 lines)',pg.evaluate("(function(){var v=document.querySelector('#tl svg');return !!v.querySelector('path.f[fill-rule=evenodd]')&&v.querySelectorAll('circle').length===1&&!!v.querySelector('path[d*=\"M12.6 6.7h8.4\"]')})()"))
        chk(label+' attachment icon = new paperclip',pg.evaluate("!!document.querySelector('#ta svg path[d^=\"M15 7l-6.5 6.5\"]')"))
        chk(label+' Edit icon still the sliders',pg.evaluate("document.querySelector('#te svg').querySelectorAll('rect').length===3"))
        chk(label+' no emoji left on screen for ☑ 📎 ✏',pg.evaluate("[].every.call(document.querySelectorAll('#t427 button'),function(b){var t=b.cloneNode(true);[].forEach.call(t.querySelectorAll('.bp-ic-t,svg'),function(x){x.remove()});return !/[☑📎✏]/.test(t.textContent)})"))
        chk(label+' Markup + Pen buttons use the pen-in-circle icon',pg.evaluate("(function(){var m=[].filter.call(document.querySelectorAll('button'),function(b){return b.getAttribute('data-tool')==='pen'||/openMarkup|openDesktopMarkup/.test(b.getAttribute('onclick')||'')});return m.length>=3&&m.every(function(b){return !!b.querySelector('svg circle[r=\"9.2\"]')})})()"))
        chk(label+' no page errors',len(e)==0)
        if e: print(e)
        if label=='field':
            chk('field drawer Punch = checklist icon',pg.evaluate("!!document.querySelector('#nav-s-punch svg path.f')"))
            pg.evaluate("toggleNavDrawer()");pg.wait_for_timeout(500);pg.screenshot(path='/tmp/v427_drawer.png')
            pg.evaluate("toggleNavDrawer()")
            pg.evaluate("document.getElementById('t427').style.fontSize='60px'");pg.wait_for_timeout(300)
            pg.locator('#t427').screenshot(path='/tmp/v427_icons.png')
    b.close()
finally:
    srv.terminate()
print('ALL PASS' if all(ok) else 'SOME FAILED',sum(ok),'/',len(ok))
