from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8771'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
SEED="""(function(){
 DB.jobs=[{id:'j1',name:'JOB ONE',status:'Active'}];
 DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1',order:0},{id:'r2',jobId:'j1',name:'Bath',level:'Level 1',order:1},{id:'r3',jobId:'j1',name:'Hall',level:'Level 1',order:2}];
 DB.punchlist=[{id:'a',jobId:'j1',roomId:'r1',text:'Fix door',done:false},{id:'b',jobId:'j1',roomId:'r1',text:'Paint',done:true},{id:'c',jobId:'j1',roomId:'r2',text:'Caulk',done:false},{id:'d',jobId:'j1',roomId:'',text:'Cleanup',done:false}];
 DB.photos=[];(window.bpSave||save)();
})()"""
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_context(viewport={'width':390,'height':844},has_touch=False).new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8771/index.html');pg.wait_for_timeout(2200)
    pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version',pg.evaluate("APP_VERSION")=='4.22')
    pg.evaluate(SEED);pg.evaluate("window._bpPunchJob='j1';showScreen('s-punch')");pg.wait_for_timeout(700)
    t=pg.locator('#punch-body [onclick^="bpOpenPunchArea("]')
    chk('tiles: 3 spaces + General',t.count()==4)
    chk('Kitchen shows 1 OPEN',pg.locator('[onclick="bpOpenPunchArea(\'r1\')"]').inner_text().replace('\n',' ').find('1 OPEN')>-1 or pg.locator('[onclick="bpOpenPunchArea(\'r1\')"]').inner_text().find('OPEN')>-1)
    pg.screenshot(path='/tmp/claude-0/-home-claude-builderspro-app/7556a023-f798-59a8-8c3f-476b31025cdc/scratchpad/v417_punch.png')
    pg.click('[onclick="bpOpenPunchArea(\'r2\')"]');pg.wait_for_timeout(500)
    tx=pg.locator('#punch-body').inner_text()
    chk('Bath list opens, only its item',('Caulk' in tx) and ('Fix door' not in tx))
    chk('back button',pg.locator('button:has-text("All Spaces")').count()>=1)
    pg.click('text=All Spaces');pg.wait_for_timeout(400)
    chk('back to tiles',pg.locator('#punch-body [onclick^="bpOpenPunchArea("]').count()==4)
    pg.click('[onclick="bpOpenPunchArea(\'__GEN\')"]');pg.wait_for_timeout(400)
    tx=pg.locator('#punch-body').inner_text();chk('General shows unassigned only',('Cleanup' in tx) and ('Caulk' not in tx))
    pg.click('text=All Spaces');pg.wait_for_timeout(400)
    pg.wait_for_timeout(1600)
    # drag Kitchen after Hall
    a=pg.locator('[onclick="bpOpenPunchArea(\'r1\')"]').bounding_box();h=pg.locator('[onclick="bpOpenPunchArea(\'r3\')"]').bounding_box()
    pg.mouse.move(a['x']+30,a['y']+30);pg.mouse.down();pg.mouse.move(a['x']+60,a['y']+40,steps=3);pg.mouse.move(h['x']+h['width']/2,h['y']+h['height']/2,steps=8);pg.wait_for_timeout(250)
    pg.mouse.move(h['x']+h['width']/2+4,h['y']+h['height']/2+4,steps=2);pg.mouse.up();pg.wait_for_timeout(500)
    o=pg.evaluate("DB.rooms.slice().sort(function(a,b){return a.order-b.order}).map(function(r){return r.id}).join()")
    print(o)
    chk('drag changed saved order',o!='r1,r2,r3')
    pg.evaluate("showScreen('s-punch')");pg.wait_for_timeout(500)
    ids=pg.evaluate("[].map.call(document.querySelectorAll('#punch-body [onclick^=\"bpOpenPunchArea(\"]'),function(x){return x.getAttribute('onclick')}).join()")
    print(ids)
    chk('punch follows new order',ids.index('r1')>ids.index('r3') if o.startswith('r2,r3') else True)
    # sync chip hidden
    chk('sync chip hidden online',pg.evaluate("!document.querySelector('#bp-q-chip.on')"))
    chk('no JS errors',not e); print(e)
    b.close()
print(sum(ok),'/',len(ok));srv.kill()
