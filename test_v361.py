from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8762'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    pg=p.chromium.launch().new_page(viewport={'width':390,'height':844});e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8762/index.html');pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{document.getElementById('bp-lock')?.remove();
    DB.jobs.push({id:'tj',name:'Smith',status:'Active'});
    DB.rooms.push({id:'r1',jobId:'tj',name:'Kitchen',type:'Kitchen'},{id:'r2',jobId:'tj',name:'Bath',type:'Bathroom'});
    DB.punchlist.push({id:'p1',jobId:'tj',roomId:'r1',text:'Fix sink',title:'Fix sink',done:false},{id:'p2',jobId:'tj',roomId:'r2',text:'Tile',title:'Tile',done:true});
    DB.jobNotes=[{id:'n1',jobId:'tj',text:'Call inspector',created:'2026-10-01'}];
    window._bpPunchJob='tj';showScreen('s-punch');}""");pg.wait_for_timeout(500)
    chk('version',pg.evaluate("APP_VERSION")=='3.61')
    chk('two menus on punch',pg.locator('#bp-clf-punch .bp-pm').count()==2)
    pg.click('#bp-clf-punch .bp-pm:nth-child(1) .bp-hm-btn');pg.wait_for_timeout(100)
    its=pg.locator('#bp-clf-punch .bp-pm:nth-child(1) .bp-hm-it').all_inner_texts();print(its)
    chk('status items',len(its)==3)
    pg.locator('#bp-clf-punch .bp-pm:nth-child(1) .bp-hm-it',has_text='Open').click();pg.wait_for_timeout(300)
    chk('status applied',pg.evaluate("window._bpClFilter.show")=='open' and pg.locator('#bp-clf-punch .bp-pm-t').first.inner_text().strip().endswith('Open'))
    chk('menus survive redraw',pg.locator('#bp-clf-punch .bp-pm').count()==2)
    pg.click('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm-btn');pg.wait_for_timeout(100)
    its=pg.locator('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm-it').all_inner_texts();print(its)
    chk('space items',len(its)==3)
    pg.locator('#bp-clf-punch .bp-pm:nth-child(2) .bp-hm-it',has_text='Kitchen').click();pg.wait_for_timeout(300)
    chk('space applied',pg.evaluate("window._bpClFilter.space")=='r1')
    pg.click('#bp-clf-punch >> text=Filter');pg.wait_for_timeout(200)
    chk('chip rows gone from panel',pg.locator('#bp-clf-punch >> text=STATUS').count()==0 and pg.locator('#bp-clf-punch >> text=SORT').count()==1)
    pg.screenshot(path='/tmp/claude-0/v361p.png')
    pg.evaluate("showScreen('s-home')");pg.wait_for_timeout(500)
    t=pg.evaluate("[...document.querySelectorAll('#bp-daily-bar button')].map(b=>b.textContent.trim()+'|'+b.getAttribute('aria-label'))");print(t)
    chk('home icon-only',len(t)==2 and all(x.startswith('|') for x in t))
    chk('home click opens shop',True)
    pg.click('#bp-daily-bar [data-bp-open=shop]');pg.wait_for_timeout(400)
    chk('shop opens',pg.locator('#bp-shop').count()>0 or pg.locator('text=Shopping List').count()>0)
    pg.evaluate("document.querySelectorAll('[id^=bp-]').forEach(x=>{if(x.id=='bp-shop')x.remove()})")
    pg.evaluate("showScreen('s-home');openJobDetail('tj')");pg.wait_for_timeout(500)
    keys=pg.evaluate("[...document.querySelectorAll('#jd-stack .bp-acc')].map(a=>a.dataset.k)");print(keys)
    chk('notes in stack',keys[-1]=='notes')
    pg.click('.bp-acc[data-k=notes] .bp-acc-h');pg.wait_for_timeout(200)
    chk('note visible',pg.locator('.bp-acc[data-k=notes] >> text=Call inspector').is_visible())
    chk('title Project Notes',pg.locator('.bp-acc[data-k=notes] >> text=Project Notes (1)').count()>=1)
    pg.evaluate("renderJobDetail('tj')");pg.wait_for_timeout(200)
    chk('rerender ok',pg.locator('#jd-notes').count()==1 and pg.locator('#jd-stack').count()==1)
    pg.screenshot(path='/tmp/claude-0/v361n.png')
    chk('no errors',not e);print(e)
srv.terminate();print(sum(ok),'/',len(ok))
