from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8769'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
PNG="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
SEED="""(function(){
 DB.jobs=[{id:'j1',name:'JOB ONE',status:'Active'},{id:'j2',name:'JOB TWO',status:'Active'}];
 DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',type:'Kitchen',level:'Level 1'}];
 DB.photos=[1,2,3,4,5].map(function(i){return {id:'p'+i,jobId:i==5?'j2':'j1',roomId:'',src:'%s',date:new Date().toISOString(),caption:i==2?'Permit sign':''}});
 DB.documents=[];DB.deletedPhotoIds={};
 (window.bpSave||save)();
})()""" % PNG
def run(name,url,vw,vh,desk):
    with sync_playwright() as p:
        b=p.chromium.launch();pg=b.new_context(viewport={'width':vw,'height':vh}).new_page();e=[]
        pg.on('pageerror',lambda x:e.append(str(x)))
        pg.goto('http://localhost:8769/'+url);pg.wait_for_timeout(2200)
        pg.evaluate("document.getElementById('bp-lock')?.remove()")
        chk(name+' version',pg.evaluate("APP_VERSION")=='4.16')
        pg.evaluate(SEED)
        if desk: pg.evaluate("showView('photos')")
        else: pg.evaluate("showScreen('s-photos')")
        pg.wait_for_timeout(500)
        pg.evaluate("bpOpenPhotoArea('UNFILED')");pg.wait_for_timeout(500)
        chk(name+' round menu + Select pill shown',pg.locator('#bpu-menu-btn').is_visible() and pg.locator('#bpu-sel').inner_text()=='Select')
        chk(name+' old File-all button & floating bar gone',pg.locator('button[onclick*=bpFileAllPrompt]').count()==0 and pg.locator('#bp-unf-bar').count()==0)
        pg.click('#bpu-sel');pg.wait_for_timeout(300)
        chk(name+' pill now says Done',pg.locator('#bpu-sel').inner_text()=='Done')
        gid='#photos-grid-wrap' if desk else '#photos-grid'
        kids=pg.locator(gid+' > div')
        chk(name+' 5 thumbs',kids.count()==5)
        kids.nth(3).click();kids.nth(4).click();pg.wait_for_timeout(200)
        chk(name+' 2 selected',pg.locator('#bp-photo-header, #bp-desk-photo-header').inner_text().find('2 selected')>-1)
        chk(name+' viewer NOT opened while selecting',pg.evaluate("!document.getElementById('photo-viewer')||getComputedStyle(document.getElementById('photo-viewer')).display=='none'||!document.getElementById('photo-viewer').classList.contains('open')"))
        pg.click('#bpu-menu-btn');pg.wait_for_timeout(300)
        r=pg.locator('.bpu-pop').bounding_box();chk(name+' menu fully on screen',r and r['x']>=0 and r['x']+r['width']<=vw and r['y']+r['height']<=vh)
        pg.screenshot(path='/tmp/claude-0/-home-claude-builderspro-app/7556a023-f798-59a8-8c3f-476b31025cdc/scratchpad/%s_menu.png'%name)
        pg.locator('.bpu-it',has_text='Assign to location').click();pg.wait_for_timeout(400)
        chk(name+' location sheet opened',pg.locator('#bp-file-sheet').count()==1)
        pg.locator('#bp-file-sheet button',has_text='Kitchen').first.click();pg.wait_for_timeout(500)
        st=pg.evaluate("DB.photos.filter(p=>p.roomId==='r1').map(p=>p.id).sort().join()")
        chk(name+' 2 photos assigned to Kitchen ('+st+')',st=='p1,p2')
        # select-all then docs: p5 is j2 (has job), all have jobs
        pg.click('#bpu-sel');pg.wait_for_timeout(300)
        pg.click('#bpu-menu-btn');pg.locator('.bpu-it',has_text='Select all').click();pg.wait_for_timeout(200)
        chk(name+' select all = 3',pg.locator('#bp-photo-header, #bp-desk-photo-header').inner_text().find('3 selected')>-1)
        pg.once('dialog',lambda d:d.accept())
        pg.locator('.bpu-pop').is_visible() or pg.click('#bpu-menu-btn')
        pg.locator('.bpu-it',has_text='Move to Documents').click();pg.wait_for_timeout(600)
        d=pg.evaluate("DB.documents.map(x=>x.jobId+':'+x.category+':'+x.fileType).sort().join()")
        chk(name+' 3 documents created ('+d+')',d=='j1:Photo:image/png,j1:Photo:image/png,j2:Photo:image/png')
        chk(name+' photos left = only the 2 filed',pg.evaluate("DB.photos.length")==2)
        chk(name+' moved ones tombstoned',pg.evaluate("Object.keys(DB.deletedPhotoIds).length")==3)
        chk(name+' recoverable (recycle)',pg.evaluate("JSON.stringify(DB.recycle||DB.recentlyDeleted||DB.deleted||{}).length>100"))
        chk(name+' back to spaces, no leftover bar',pg.locator('#bp-unf-bar').count()==0 and pg.evaluate("window._bpPhotoArea")is None)
        chk(name+' no page errors',not e);print(e)
        b.close()
run('phone','index.html',390,844,False)
run('ipad','index.html',834,1194,False)
run('desktop','desktop.html',1440,900,True)
srv.terminate();print(sum(ok),'/',len(ok))
