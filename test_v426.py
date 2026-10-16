from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8780'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
INJECT="""(function(){var h=document.createElement('div');h.id='t426';h.style.cssText='position:fixed;top:60px;left:10px;z-index:99999;background:#111;color:#fff;padding:12px;display:flex;gap:14px;font-size:22px';
h.innerHTML='<button id="tb">✏️ Edit</button><span id="tp"><i class="bp-hm-ic">✏️</i></span><button id="tc">✏️</button>';document.body.appendChild(h);})()"""
try:
  with sync_playwright() as p:
    b=p.chromium.launch()
    for page,label in (('index.html','field'),('desktop.html','desktop')):
        pg=b.new_context(viewport={'width':1000 if label=='desktop' else 390,'height':800}).new_page();e=[];pg.on('pageerror',lambda x:e.append(str(x)))
        pg.goto('http://localhost:8780/'+page);pg.wait_for_timeout(2500);pg.evaluate("document.getElementById('bp-lock')?.remove()")
        chk(label+' version 4.26',pg.evaluate("APP_VERSION")=='4.26')
        pg.evaluate(INJECT);pg.wait_for_timeout(1200)
        for sel,name in (('#tb','Edit button'),('#tp','menu-item icon'),('#tc','icon-only button')):
            chk(label+' '+name+' = sliders (3 knobs, 3 lines)',pg.evaluate("(function(){var e=document.querySelector('%s');var v=e.querySelector('svg');return v.querySelectorAll('rect').length===3&&!!v.querySelector('path[d*=\"M3 5h9\"]')})()"%sel))
        chk(label+' no pencil emoji left on screen in those',pg.evaluate("[].every.call(document.querySelectorAll('#t426 *'),function(n){var s=getComputedStyle(n);return !(n.children.length===0&&n.textContent.indexOf('✏')>=0&&s.color!=='rgba(0, 0, 0, 0)'&&s.fontSize!=='0px'&&s.visibility!=='hidden'&&s.opacity!=='0'&&!n.classList.contains('bp-ic-t')&&!(n.closest&&n.closest('.bp-ic-t')))})"))
        chk(label+' Markup/Pen buttons still a pencil',pg.evaluate("(function(){var m=[].filter.call(document.querySelectorAll('button'),function(b){return b.getAttribute('data-tool')==='pen'||/openMarkup|openDesktopMarkup/.test(b.getAttribute('onclick')||'')});return m.length>=3&&m.every(function(b){var v=b.querySelector('svg');return v.querySelectorAll('rect').length===0&&!!v.querySelector('path[d*=\"M13.5 6.5l4 4\"]')})})()"))
        chk(label+' no page errors',len(e)==0)
        if e: print(e)
        if label=='field':
            pg.evaluate("document.getElementById('t426').style.fontSize='64px'");pg.wait_for_timeout(300)
            pg.locator('#t426').screenshot(path='/tmp/v426_icons.png')
    b.close()
finally:
    srv.terminate()
print('ALL PASS' if all(ok) else 'SOME FAILED',sum(ok),'/',len(ok))
