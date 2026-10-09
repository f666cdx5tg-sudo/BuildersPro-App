"""Balance audit: buttons that sit side by side (same row) must be the same height, and
icon-only buttons the same width. Run: python3 test_balance.py [desktop|field]  (exit 1 if any imbalance)"""
import os, sys, re
from playwright.sync_api import sync_playwright
mode = sys.argv[1] if len(sys.argv)>1 else 'desktop'
URL = 'http://localhost:8799/' + ('desktop.html' if mode=='desktop' else 'index.html')
VP = (1440,900) if mode=='desktop' else (390,844)
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'test_command_center_icons.py')).read()
SEED=re.search(r'SEED = """(.*?)"""',src,re.S).group(1)
SP=eval(re.search(r'SPACES = (\[.*?\])\nTYPES',src,re.S).group(1)); TY=eval(re.search(r'TYPES = (\[.*?\])\n',src,re.S).group(1))
EXTRA="""()=>{DB.documents=[{id:'d1',jobId:'jobT',name:'Doc',category:'Other',fileSrc:'data:text/plain;base64,aGk=',fileName:'a.txt',fileType:'text/plain',notes:'n',created:new Date().toISOString()}];
 DB.recycle=[{id:'rc1',coll:'expenses',rec:{id:'e9'},label:'Item',deletedAt:new Date().toISOString()},{id:'rc2',coll:'expenses',rec:{id:'e8'},label:'Item2',deletedAt:new Date().toISOString()}];
 DB.tombstones={'expenses:o1':new Date().toISOString(),'expenses:o2':new Date().toISOString()};}"""
SCAN="""()=>{
 function vis(e){var r=e.getBoundingClientRect();var cs=getComputedStyle(e);return r.width>4&&r.height>4&&cs.visibility!=='hidden'&&cs.display!=='none'&&e.offsetParent!==null}
 function isBtn(e){return e.tagName==='BUTTON'||e.getAttribute('role')==='button'||/\\bbtn\\b/.test(e.className)}
 function iconOnly(e){return (e.textContent||'').replace(/\\s+/g,'').length<=2}
 var out=[],seen=new Set();
 document.querySelectorAll('body *').forEach(function(p){
   if(seen.has(p))return; var kids=Array.prototype.filter.call(p.children,function(c){return isBtn(c)&&vis(c)&&!c.closest('[data-bp-nozoom]')});
   if(kids.length<2)return; seen.add(p);
   // same row only
   var rows={};kids.forEach(function(k){var r=k.getBoundingClientRect();var key=Math.round((r.top+r.height/2)/10);(rows[key]=rows[key]||[]).push(k)});
   Object.keys(rows).forEach(function(key){var g=rows[key];if(g.length<2)return;
     var hs=g.map(function(k){return k.getBoundingClientRect().height}),mx=Math.max.apply(0,hs),mn=Math.min.apply(0,hs);
     var bad=mx-mn>3;
     var io=g.filter(iconOnly);var ws=io.map(function(k){return k.getBoundingClientRect().width});
     var wbad=io.length>1&&Math.max.apply(0,ws)-Math.min.apply(0,ws)>3;
     if(bad||wbad)out.push({h:hs.map(Math.round),w:g.map(function(k){return Math.round(k.getBoundingClientRect().width)}),t:g.map(function(k){return (k.textContent||k.title||'').trim().slice(0,14)||(k.className||'').toString().slice(0,12)}),ctx:(p.id||p.className||p.tagName).toString().slice(0,30)});
   });
 });return out;}"""
bad={}
with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':VP[0],'height':VP[1]}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate("document.getElementById('bp-lock')?.remove()"); pg.wait_for_timeout(800)
    pg.evaluate(SEED,[SP,TY]); pg.evaluate(EXTRA)
    if mode=='desktop':
        for v in ['dashboard','jobs','job-detail','rooms','photos','punchlist','documents','eod','finance','estimates','calendar','time','contacts','archive','sync','search']:
            try: pg.evaluate("(v)=>showView(v)",v)
            except Exception: continue
            pg.wait_for_timeout(500)
            if v=='sync': pg.evaluate("bpRenderRecycle()")
            r=pg.evaluate(SCAN)
            if r: bad[v]=r
    else:
        pg.evaluate("showScreen('s-job-detail');currentJobId='jobT';renderJobDetail('jobT')"); pg.wait_for_timeout(900)
        r=pg.evaluate(SCAN)
        if r: bad['job-detail']=r
        for sec in ['spaces','punchlist','documents','finance','photos','appointments','walkthrough','reports','contractors']:
            try: pg.evaluate("(s)=>{try{bpOpenJobSection(s,'jobT')}catch(e){}}",sec)
            except Exception: pass
            pg.wait_for_timeout(700); r=pg.evaluate(SCAN)
            if r: bad['job:'+sec]=r
        try: pg.evaluate("bpCloseSectionFocus()")
        except Exception: pass
        for sc in ['s-home','s-jobs','s-calendar']:
            try: pg.evaluate("(s)=>showScreen(s)",sc); pg.wait_for_timeout(700); r=pg.evaluate(SCAN); 
            except Exception: continue
            if r: bad[sc]=r
        try:
            pg.evaluate("openSheet('sheet-sync')"); pg.evaluate("bpRenderRecycle()"); pg.wait_for_timeout(700); r=pg.evaluate(SCAN)
            if r: bad['sync sheet']=r
        except Exception: pass
    b.close()
n=0
for v,items in bad.items():
    print('SCREEN',v)
    seen=set()
    for it in items:
        k=(tuple(it['h']),tuple(it['t']))
        if k in seen: continue
        seen.add(k); n+=1; print('  heights',it['h'],'widths',it['w'],it['t'],'in',it['ctx'])
print('RESULT:', 'PASS balanced' if not n and not errs else f'FAIL {n} imbalanced groups', errs[:2])
sys.exit(1 if n or errs else 0)
