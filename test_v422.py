from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8776'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_context(viewport={'width':390,'height':844}).new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8776/index.html');pg.wait_for_timeout(2200);pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version',pg.evaluate("APP_VERSION")=='4.23')
    pg.evaluate("DB.jobs=[{id:'j1',name:'J',status:'Active'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',level:'Level 1'}];DB.punchlist=[];(window.bpSave||save)();openAddPunchItem('j1','r1')")
    pg.wait_for_timeout(600)
    chk('closed: no category list showing',pg.locator('#pa-cats [data-cat]').count()==0)
    chk('single button',pg.locator('#pa-cats > button').count()==1 and 'Choose a category' in pg.locator('#pa-cats').inner_text())
    pg.screenshot(path='/tmp/claude-0/-home-claude-builderspro-app/7556a023-f798-59a8-8c3f-476b31025cdc/scratchpad/c1.png')
    pg.click('#pa-cats > button');pg.wait_for_timeout(200)
    n=pg.locator('#pa-cats [data-cat]').count();chk('opens list of categories (%d)'%n,n>3)
    pg.screenshot(path='/tmp/claude-0/-home-claude-builderspro-app/7556a023-f798-59a8-8c3f-476b31025cdc/scratchpad/c2.png')
    pg.locator('#pa-cats [data-cat]').nth(1).click();pg.wait_for_timeout(200)
    chk('picking closes list & shows choice',pg.locator('#pa-cats [data-cat]').count()==0 and 'Choose a category' not in pg.locator('#pa-cats').inner_text())
    pg.click('#pa-add');pg.wait_for_timeout(400)
    chk('item added',pg.evaluate("DB.punchlist.length")==1)
    chk('no JS errors',not e);print(e)
print(sum(ok),'/',len(ok));srv.kill()
