from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8763'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)
import base64,struct,zlib
def png():
    raw=b'\x00\xff\x00\x00'*4
    def ch(t,d):
        c=struct.pack('>I',len(d))+t+d;return c+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',2,2,8,6,0,0,0)[:13])+ch(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\xff\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\x00\x00\xff\x00\xff'[:10]*0+(b'\x00'+b'\xff\x00\x00\xff'*2)*2))+ch(b'IEND',b'')
open('/tmp/claude-0/t.png','wb').write(png())
with sync_playwright() as p:
    b=p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
    ctx=b.new_context(viewport={'width':390,'height':844},permissions=['microphone'])
    pg=ctx.new_page();e=[]
    pg.on('pageerror',lambda x:e.append(str(x)))
    pg.goto('http://localhost:8763/index.html');pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{document.getElementById('bp-lock')?.remove();
    DB.jobs.push({id:'tj',name:'Smith',status:'Active'});DB.rooms.push({id:'r1',jobId:'tj',name:'Kitchen',type:'Kitchen'});
    bpSetActiveJob && bpSetActiveJob('tj',true);showScreen('s-home');renderHome&&renderHome()}""");pg.wait_for_timeout(600)
    chk('version',pg.evaluate("APP_VERSION")=='3.62')
    t=pg.evaluate("[...document.querySelectorAll('#bp-daily-bar button')].map(b=>b.getAttribute('aria-label')+'|'+b.textContent.trim())");print(t)
    chk('3 icon buttons',len(t)==3 and t[2].startswith('Notes|'))
    pg.click('#bp-daily-bar [data-bp-open=notes]');pg.wait_for_timeout(300)
    chk('list opens',pg.locator('#bp-notes-ov h2').inner_text()=='Notes')
    pg.click('#bp-notes-ov [aria-label="New note"]');pg.wait_for_timeout(200)
    chk('body blank',pg.input_value('#bpn-text')=='')
    ti=pg.input_value('#bpn-title');print(ti)
    import datetime
    chk('title = date + Whole job',ti.startswith(datetime.date.today().strftime('%m/%d/%Y')) and 'Whole job' in ti)
    pg.select_option('#bpn-room','r1');pg.wait_for_timeout(100)
    ti=pg.input_value('#bpn-title');print(ti);chk('title follows space',ti.endswith('Kitchen'))
    pg.set_input_files('#bpn-file','/tmp/claude-0/t.png');pg.wait_for_timeout(800)
    chk('photo added',pg.locator('#bp-notes-ov .nt').count()==1)
    pg.click('#bpn-rec');pg.wait_for_timeout(1800)
    chk('recording state',pg.locator('#bpn-rec.rec').count()==1)
    pg.click('#bpn-rec');pg.wait_for_timeout(1200)
    chk('audio added',pg.locator('#bp-notes-ov audio').count()==1)
    pg.screenshot(path='/tmp/claude-0/v362.png')
    pg.click('#bp-notes-ov .nb.pri');pg.wait_for_timeout(400)
    n=pg.evaluate("DB.jobNotes[0]")
    chk('saved w/ photo+audio+no text',len(n['photos'])==1 and len(n['audio'])==1 and n['text']=='' and n['roomId']=='r1')
    chk('back in list with card',pg.locator('#bp-notes-ov .nc').count()==1)
    pg.click('#bp-notes-ov .nc');pg.wait_for_timeout(200)
    pg.fill('#bpn-title','Custom title');pg.fill('#bpn-text','hello');pg.click('#bp-notes-ov .nb.pri');pg.wait_for_timeout(300)
    chk('custom title kept',pg.evaluate("DB.jobNotes[0].title")=='Custom title')
    pg.click('[aria-label=Close]');pg.wait_for_timeout(200)
    pg.evaluate("openJobDetail('tj')");pg.wait_for_timeout(500)
    pg.click('.bp-acc[data-k=notes] .bp-acc-h');pg.wait_for_timeout(200)
    chk('job page note card',pg.locator('.bp-acc[data-k=notes] >> text=Custom title').is_visible())
    pg.click('.bp-acc[data-k=notes] >> text=+ Add Note');pg.wait_for_timeout(200)
    chk('add from job opens editor w/ job',pg.locator('#bpn-job').input_value()=='tj')
    chk('no errors',not e);print(e)
srv.terminate();print(sum(ok),'/',len(ok))
