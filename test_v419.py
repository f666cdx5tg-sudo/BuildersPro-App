"""v4.19 — Full Day PDF report. Builds a real PDF from seeded data in BOTH apps,
checks it is a valid multi-page PDF with every checklist item + every photo,
and walks the Send-to-client chooser -> build -> ready sheet.
Usage: python3 test_v419.py [outdir]"""
from playwright.sync_api import sync_playwright
import subprocess, time, base64, sys, os, re
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
srv = subprocess.Popen(['python3', '-m', 'http.server', '8773'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
ok = []
def chk(n, c): ok.append(bool(c)); print(('PASS ' if c else 'FAIL ') + n)

SEED = """(function(){
 function img(c,w,h,label){var cv=document.createElement('canvas');cv.width=w;cv.height=h;var g=cv.getContext('2d');
   g.fillStyle=c;g.fillRect(0,0,w,h);g.fillStyle='rgba(255,255,255,.85)';g.font='bold 90px sans-serif';g.fillText(label,40,h/2);
   g.strokeStyle='#fff';g.lineWidth=8;g.strokeRect(20,20,w-40,h-40);return cv.toDataURL('image/jpeg',.8);}
 var t=new Date(),pad=function(n){return (n<10?'0':'')+n},today=t.getFullYear()+'-'+pad(t.getMonth()+1)+'-'+pad(t.getDate());
 var nowIso=t.toISOString(),old=new Date(t.getTime()-5*864e5).toISOString();
 DB.jobs=[{id:'j1',name:'123 Maple Street Gut Renovation',address:'123 Maple St, Bergenfield NJ',client:'Pat Rivera',clientEmail:'pat@example.com',clientPhone:'201-555-0100',status:'Active'}];
 DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',order:0},{id:'r2',jobId:'j1',name:'Master Bath',order:1},{id:'r3',jobId:'j1',name:'Basement',order:2},{id:'r4',jobId:'j1',name:'Empty Room',order:3}];
 var P=[];
 function add(room,text,done,when,extra){P.push({id:'p'+P.length,jobId:'j1',roomId:room,text:text,done:done,completedAt:done?when:undefined,extraNotes:extra||'',photosBefore:[],photosAfter:[]});}
 add('r1','Rough-in supply lines for sink and dishwasher',true,nowIso);
 add('r1','Install gas line to range with shutoff and pressure test — inspector to witness before closing the wall, coordinate with the utility for the meter release',true,nowIso,'Passed 10 min @ 30 psi');
 add('r1','Set cabinets',true,old);
 add('r1','Backsplash tile',false);
 add('r1','Final plumbing trim and fixtures',false);
 add('r2','Pressure-test drain lines',true,nowIso);
 add('r2','Set tub and valve body',true,old);
 add('r2','Vanity top and faucet',false);
 add('r2','Shower door',false);
 add('r3','Backflow preventer install',true,nowIso);
 add('r3','Sump pit and discharge',false);
 add('', 'Dumpster swap Thursday',false);
 add('', 'Permit card posted at front door',true,old);
 // item photos
 P[0].photosAfter=[{src:img('#0a84ff',900,675,'KIT after'),date:nowIso}];
 P[1].photosBefore=[{src:img('#a855f7',900,675,'GAS before'),date:nowIso}];
 P[1].photosAfter=[{src:img('#16a34a',900,675,'GAS after'),date:nowIso},{src:img('#ea580c',900,675,'GAS test'),date:nowIso}];
 P[9].completionPhoto=img('#0891b2',900,675,'BFP done');P[9].completionPhotoDate=nowIso;
 P[2].photosAfter=[{src:img('#555',900,675,'OLD DAY'),date:old}]; // not today -> must NOT appear
 DB.punchlist=P;
 var cols=['#dc2626','#2563eb','#059669','#d97706','#7c3aed','#db2777','#0d9488','#4b5563'];
 DB.photos=[];
 for(var i=0;i<8;i++){DB.photos.push({id:'ph'+i,jobId:'j1',roomId:i<3?'r1':(i<5?'r2':(i<6?'r3':'')),src:img(cols[i],i%2?1000:700,i%2?750:900,'PHOTO '+(i+1)),date:nowIso,caption:i==0?'Gas line before closing the wall':''});}
 DB.photos.push({id:'phold',jobId:'j1',roomId:'r1',src:img('#000',400,300,'OLD'),date:old}); // other day -> excluded
 DB.reports=[{id:'rep1',jobId:'j1',date:today,dprNumber:'DPR-007',workers:4,weather:'Sunny 68F',progress:62,
   completed:'Finished rough-in on kitchen supply lines.\\nGas line pressure-tested and passed.\\nBackflow preventer installed in the basement.',
   incomplete:'Waiting on tub valve trim from supplier.',tomorrow:'Set vanity top, start backsplash prep.',safety:'Toolbox talk on trench safety.',
   clientNotes:'Inspector signed off on the gas line today. Tile selection needed by Friday.',createdBy:'Stan',createdAt:nowIso}];
 (window.bpSave||window.saveDB||window.save)();
 return today;
})()"""

BUILD = """async()=>{
  var r=await window.bpBuildDayPdf({reportId:'rep1'});
  var buf=new Uint8Array(await r.blob.arrayBuffer()),s='';
  for(var i=0;i<buf.length;i+=32768)s+=String.fromCharCode.apply(null,buf.subarray(i,i+32768));
  return {b64:btoa(s),pages:r.pages,total:r.total,doneAll:r.doneAll,doneToday:r.doneToday,photos:r.photos,size:buf.length};
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for app in ('index.html', 'desktop.html'):
        tag = app.split('.')[0]
        ctx = b.new_context(viewport={'width': 390, 'height': 844} if tag == 'index' else {'width': 1400, 'height': 900})
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto('http://localhost:8773/' + app); pg.wait_for_timeout(2200)
        pg.evaluate("document.getElementById('bp-lock')?.remove()")
        chk(tag + ': version 4.19+', pg.evaluate('APP_VERSION') in ('4.19', '4.20', '4.21'))
        pg.evaluate(SEED); pg.wait_for_timeout(300)
        res = pg.evaluate(BUILD)
        raw = base64.b64decode(res['b64']); path = os.path.join(OUT, 'v419_%s.pdf' % tag); open(path, 'wb').write(raw)
        chk(tag + ': is a PDF', raw[:5] == b'%PDF-' and raw.rstrip().endswith(b'%%EOF'))
        info = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
        npg = int(re.search(r'Pages:\s+(\d+)', info).group(1))
        chk(tag + ': pdfinfo reads %d pages, matches builder' % npg, npg == res['pages'] and npg >= 2)
        chk(tag + ': all 13 checklist items counted (6 done, 3 today... )', res['total'] == 13 and res['doneAll'] == 7 and res['doneToday'] == 4)
        # 4 item photos today + 8 day photos (old-day ones excluded) = 12
        print('photos=',res['photos'],'pages=',res['pages'],'size=',res['size']); chk(tag + ': 13 photos today = 5 on checklist items + 8 day photos (other-day photos left out)', res['photos'] == 13)
        subprocess.run(['pdftoppm', '-r', '70', '-png', path, os.path.join(OUT, 'v419_%s' % tag)])
        # chooser -> build -> ready sheet
        pg.evaluate("(function(){var f=window.currentJobId;})()")
        pg.evaluate("bpSendEod('rep1')"); pg.wait_for_timeout(300)
        sheet = pg.inner_text('#bp-send-sheet')
        chk(tag + ': chooser leads with Full Day PDF', 'Full Day PDF' in sheet and 'Email summary only' in sheet)
        pg.evaluate("bpSendPick('report','rep1')"); pg.wait_for_function("document.getElementById('bp-daypdf') && /PDF ready/.test(document.getElementById('bp-daypdf').innerText)", timeout=60000)
        ui = pg.inner_text('#bp-daypdf')
        print(repr(ui)); chk(tag + ': ready sheet shows counts + client email', '13 checklist items' in ui and '13 photos' in ui and 'pat@example.com' in ui)
        chk(tag + ': old Photo Report entry now opens the PDF flow', pg.evaluate("window.bpOpenPhotoReport.toString().indexOf('bpDayPdf')>-1"))
        chk(tag + ': job-level Client Update also gives the PDF', pg.evaluate("window.exportClientUpdate.toString().indexOf('bpDayPdfForJob')>-1"))
        pg.screenshot(path=os.path.join(OUT, 'v419_%s_sheet.png' % tag))
        chk(tag + ': no JS errors', not errs); print(errs)
        ctx.close()
    # share path: stub the Web Share API and confirm the PDF is handed over AS A FILE
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda x: errs.append(str(x)))
    pg.goto('http://localhost:8773/index.html'); pg.wait_for_timeout(2000); pg.evaluate("document.getElementById('bp-lock')?.remove()")
    pg.evaluate(SEED)
    pg.evaluate("""(function(){ window.__shared=null; /* share_stub */
      navigator.canShare=function(d){return !!(d&&d.files&&d.files.length)};
      navigator.share=function(d){window.__shared={n:d.files[0].name,t:d.files[0].type,sz:d.files[0].size,title:d.title,text:d.text};return Promise.resolve();}; })()""")
    pg.evaluate("bpDayPdf('rep1')"); pg.wait_for_function("document.getElementById('bp-daypdf') && /PDF ready/.test(document.getElementById('bp-daypdf').innerText)", timeout=60000)
    ui = pg.inner_text('#bp-daypdf')
    chk('share path: primary button is Email / send the PDF (attached)', 'Email / send the PDF' in ui and 'attached' in ui)
    pg.click('text=Email / send the PDF'); pg.wait_for_timeout(300)
    sh = pg.evaluate('window.__shared'); print(sh)
    chk('share hands over a real PDF file', sh and sh['t'] == 'application/pdf' and sh['n'].endswith('.pdf') and sh['sz'] > 50000)
    chk('share carries subject + body', sh and 'DPR-007' in sh['title'] and 'Pat Rivera' in sh['text'] and '13 photos' in sh['text'])
    chk('no JS errors (share)', not errs)
    ctx.close()
    # job with NO eod today still builds
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda x: errs.append(str(x)))
    pg.goto('http://localhost:8773/index.html'); pg.wait_for_timeout(2000); pg.evaluate("document.getElementById('bp-lock')?.remove()")
    pg.evaluate(SEED); pg.evaluate("DB.reports=[]")
    r2 = pg.evaluate("async()=>{var r=await window.bpBuildDayPdf({jobId:'j1'});return {pages:r.pages,total:r.total,size:r.blob.size}}")
    chk('no-EOD job still builds full PDF', r2['pages'] >= 1 and r2['total'] == 13)
    chk('no JS errors (no-EOD)', not errs)
    b.close()
print(sum(ok), '/', len(ok)); srv.kill()
sys.exit(0 if all(ok) else 1)
