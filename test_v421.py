from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8775'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
SEED="""(function(){
 DB.jobs=[{id:'j1',name:'JOB ONE',status:'Active'}];
 DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1',order:0},{id:'r2',jobId:'j1',name:'Bath',level:'Level 1',order:1},{id:'r3',jobId:'j1',name:'Hall',level:'Level 2',order:0},{id:'r4',jobId:'j1',name:'Den',level:'Level 2',order:1}];
 DB.punchlist=[];DB.photos=[];(window.bpSave||save)();})()"""
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
    pg=ctx.new_page();e=[];pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8775/index.html');pg.wait_for_timeout(2200);pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version',pg.evaluate("APP_VERSION")=='4.23')
    cdp=ctx.new_cdp_session(pg)
    def T(t,x,y): cdp.send('Input.dispatchTouchEvent',{'type':t,'touchPoints':([{'x':x,'y':y}] if t!='touchEnd' else [])})
    def lv(i): return pg.evaluate("DB.rooms.find(function(r){return r.id=='%s'}).level"%i)
    def drag(sel_from,sel_to):
        a=pg.locator(sel_from).bounding_box();x,y=a['x']+40,a['y']+40
        T('touchStart',x,y);pg.wait_for_timeout(500)
        for i in range(1,13):
            h=pg.locator(sel_to).first.bounding_box();tx,ty=h['x']+h['width']/2,h['y']+h['height']/2
            T('touchMove',x+(tx-x)*min(i,10)/10,y+(ty-y)*min(i,10)/10);pg.wait_for_timeout(90)
        pg.wait_for_timeout(200);T('touchEnd',0,0);pg.wait_for_timeout(600)
    for name,js,pre,fn in [('spaces',"window._bpAreaJob='j1';showScreen('s-rooms')",'openRoomDetail','openRoomDetail'),('photos',"window._bpPhotoArea=null;showScreen('s-photos')",'bpOpenPhotoArea','bpOpenPhotoArea')]:
        pg.evaluate(SEED);pg.evaluate(js);pg.wait_for_timeout(800)
        sel=lambda i:'[onclick="%s(\'%s\')"]'%(pre,i)
        drag(sel('r1'),sel('r3'))
        chk(name+' Kitchen moved onto a Level 2 tile -> Level 2',lv('r1')=='Level 2')
        chk(name+' room not opened',pg.evaluate("!document.querySelector('#s-room-detail.active')"))
        pg.evaluate(js);pg.wait_for_timeout(700)
        drag(sel('r4'),'[data-bp-level="Level 1"]' if name=='spaces' else '[data-bp-lvl3]:has-text("Level 1")')
        print(pg.evaluate("DB.rooms.map(function(r){return r.id+':'+r.level+':'+r.order}).join()"));chk(name+' Den dropped on Level 1 header -> Level 1',lv('r4')=='Level 1')
        pg.evaluate(js);pg.wait_for_timeout(700)
        txt=pg.evaluate("[].map.call(document.querySelectorAll('[data-bp-level],[data-bp-lvl3]'),function(h){return h.textContent.replace(/\\s+/g,' ').slice(0,30)}).join(' | ')")
        print(txt)
    chk('no JS errors',not e);print(e)
print(sum(ok),'/',len(ok));srv.kill()
