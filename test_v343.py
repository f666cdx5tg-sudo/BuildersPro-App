"""BuildersPro v3.43 layout + thumb-reach test.  Run: python3 test_v343.py  (needs playwright + chromium)
Serves the repo folder itself, so run it from the repo root. Exit code 0 = all pass."""
import sys, os, subprocess, time
import asyncio, re, json
from playwright.async_api import async_playwright

AUDIT_JS = r"""
window.__audit = function(rootSel, opts){
  const root = document.querySelector(rootSel);
  if(!root) return {error:'no root '+rootSel};
  const vw = innerWidth;
  const out = {overflowX:null, offscreen:[], overlap:[], small:[], clipped:[], fab:[]};
  const hidden = (e)=>{ for(let n=e;n&&n!==document.documentElement;n=n.parentElement){ const cs=getComputedStyle(n); if(cs.display==='none'||cs.visibility==='hidden') return true; } return false; };
  const lbl = (e)=> (e.id?('#'+e.id):'') + ((typeof e.className==='string'&&e.className.trim())?'.'+e.className.trim().split(/\s+/).slice(0,2).join('.'):'') + ' "' + String(e.innerText||e.value||e.getAttribute('aria-label')||e.getAttribute('title')||'').trim().replace(/\s+/g,' ').slice(0,28) + '"';
  const hScroller = (e)=>{ for(let n=e.parentElement;n&&n!==root.parentElement;n=n.parentElement){ const cs=getComputedStyle(n); if((cs.overflowX==='auto'||cs.overflowX==='scroll')&&n.scrollWidth>n.clientWidth+1) return true; } return false; };
  out.overflowX = root.scrollWidth > root.clientWidth + 2 ? [root.scrollWidth, root.clientWidth] : null;
  const atoms = [];
  const sel = 'button, a[href], select, input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]), textarea, [onclick], label.btn, [role=button]';
  root.querySelectorAll(sel).forEach(e=>{
    if(hidden(e)) return; const r=e.getBoundingClientRect(); if(r.width<2||r.height<2) return;
    if(e.closest('.bp-voice-fab,#bp-voice-fab')) return;
    atoms.push({e, r, kind:'ui', label:lbl(e)});
  });
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while(walker.nextNode()){
    const t = walker.currentNode; if(!t.nodeValue.trim()) continue;
    const p = t.parentElement; if(!p || hidden(p)) continue;
    if(/^(SCRIPT|STYLE|OPTION|OPTGROUP)$/.test(p.tagName)) continue;
    const rg = document.createRange(); rg.selectNodeContents(t);
    // text inside an interactive atom is part of it (not a separate atom)
    if(p.closest(sel) && root.contains(p.closest(sel))) continue;
    const pcs=getComputedStyle(p), clip=(pcs.overflowX==='hidden'||pcs.overflow==='hidden')?p.getBoundingClientRect():null;
    [...rg.getClientRects()].forEach(r0=>{ let r=r0; if(clip){ const L=Math.max(r0.left,clip.left), R=Math.min(r0.right,clip.right); r={left:L,right:R,top:r0.top,bottom:r0.bottom,width:R-L,height:r0.height}; } if(r.width<2||r.height<2) return; atoms.push({e:p, r, kind:'text', label:lbl(p)+' [text]'}); });
  }
  const inter = (a,b)=>{ const w=Math.min(a.right,b.right)-Math.max(a.left,b.left), h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top); return [w,h]; };
  for(let i=0;i<atoms.length;i++){
    const a=atoms[i];
    if(!hScroller(a.e) && (a.r.left < -1 || a.r.right > vw + 1)) out.offscreen.push(a.label+' L'+Math.round(a.r.left)+' R'+Math.round(a.r.right));
    if(a.kind==='ui' && Math.min(a.r.width,a.r.height) < 40) out.small.push(a.label+' '+Math.round(a.r.width)+'x'+Math.round(a.r.height));
    if(a.kind==='text'){ const cs=getComputedStyle(a.e); if((cs.overflow==='hidden'||cs.overflowX==='hidden'||cs.textOverflow==='ellipsis') && a.e.scrollWidth>a.e.clientWidth+1) out.clipped.push(a.label); }
    for(let j=i+1;j<atoms.length;j++){
      const b=atoms[j];
      if(a.e===b.e || a.e.contains(b.e) || b.e.contains(a.e)) continue;
      const [w,h]=inter(a.r,b.r);
      if(w>3 && h>3) out.overlap.push(a.label+'  <>  '+b.label+'  ('+Math.round(w)+'x'+Math.round(h)+')');
    }
  }
  // fixed-position helpers (dock buttons, voice button) must not cover a tappable thing, nor each other
  if (opts && opts.fab) {
    const fx = [...document.querySelectorAll('#bp-dock button, #bp-voice-fab')].filter(f=>!hidden(f) && f.getBoundingClientRect().width>10);
    fx.forEach(f=>{ const fr=f.getBoundingClientRect();
      atoms.forEach(a=>{ if(a.kind!=='ui'||a.e===f||f.contains(a.e)) return; const [w,h]=inter(fr,a.r); if(w>3&&h>3) out.fab.push(lbl(f)+' covers '+a.label); });
      if (fr.right > vw + 1 || fr.left < -1 || fr.bottom > innerHeight + 1) out.fab.push(lbl(f)+' is off screen');
    });
    for(let i=0;i<fx.length;i++) for(let j=i+1;j<fx.length;j++){ const [w,h]=inter(fx[i].getBoundingClientRect(),fx[j].getBoundingClientRect()); if(w>1&&h>1) out.fab.push(lbl(fx[i])+' overlaps '+lbl(fx[j])); }
  }
  return out;
};
"""

SEED_JS = r"""
(()=>{
  const n = new Date(); const y=n.getFullYear(), m=n.getMonth();
  const ds = (d)=> y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');
  DB.jobs = [
   {id:'j1', name:'1536 N. Peach St', status:'Active', client:'Shelden Washington', address:'1536 N. Peach St', city:'Philadelphia', state:'PA', zip:'19131', clientEmail:'s@example.com', clientPhone:'2155551234', contractValue:48500, startDate:ds(3), completionDate:ds(27), created:now()},
   {id:'j2', name:'1234 Extremely Long Street Name Boulevard Apartment Complex Unit 5', status:'Pending', client:'Q', address:'b', contractValue:1200, startDate:ds(8), completionDate:'', created:now()}
  ];
  DB.rooms = [
   {id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', space:'Interior', kind:'room', level:'Level 1', created:now()},
   {id:'r2', jobId:'j1', name:'Master Bathroom', type:'Bathroom', space:'Interior', kind:'room', level:'Level 2', created:now()},
   {id:'r3', jobId:'j1', name:'Roof', type:'Roof', space:'Exterior', kind:'location', level:'Roof', created:now()},
   {id:'r4', jobId:'j1', name:'Basement Boiler Room', type:'Basement', space:'Interior', kind:'room', level:'Basement', created:now()}
  ];
  DB.punchlist = [
   {id:'p1', jobId:'j1', roomId:'r1', text:'Replace kitchen sink faucet and supply lines', trade:'Plumbing', value:350, priority:'High', done:false, tasks:[], photosBefore:[], photosAfter:[], created:now(), updatedAt:now()},
   {id:'p2', jobId:'j1', roomId:'r2', text:'Install new toilet', trade:'Plumbing', value:0, priority:'Normal', done:true, tasks:[], photosBefore:[], photosAfter:[], created:now(), updatedAt:now()},
   {id:'p3', jobId:'j1', roomId:'r4', text:'Replace boiler expansion tank', trade:'Heating', value:0, priority:'Normal', done:false, tasks:[{id:'t1',text:'Drain system',done:false}], photosBefore:[], photosAfter:[], created:now(), updatedAt:now()}
  ];
  DB.invoices = [
   {id:'i1', jobId:'j1', desc:'Deposit', amount:12000, date:ds(2), status:'Paid', created:now()},
   {id:'i2', jobId:'j1', desc:'Rough-in draw', amount:18000, date:ds(15), status:'Sent', created:now()}
  ];
  DB.expenses = [
   {id:'e1', jobId:'j1', desc:'Copper pipe and fittings', amount:642.18, date:ds(4), category:'Materials', vendor:'Ferguson', items:[], created:now()},
   {id:'e2', jobId:'j1', desc:'Dumpster rental', amount:480, date:ds(5), category:'Other', vendor:'', items:[], created:now()}
  ];
  DB.contractors = [{id:'c1', name:'Electrician Joe', jobId:'j1', trade:'Electrical', value:4200, scope:'Panel upgrade', start:ds(10), end:ds(12), phone:'2155550000', status:'Active', created:now()}];
  DB.permits = [{id:'pm1', jobId:'j1', trade:'Plumbing', permitNumber:'P-1001', cost:150, issueDate:ds(1), expirationDate:ds(22), status:'Active', notes:'', created:now()}];
  DB.appointments = [
   {id:'a1', title:'Inspection', type:'Appointment', date:ds(6), time:'09:00', jobId:'j1', notes:'', created:now()},
   {id:'a2', title:'Permit filing due', type:'Due Date', date:ds(9), time:'', jobId:'j1', notes:'', created:now()},
   {id:'a3', title:'Fixtures delivery', type:'Delivery', date:ds(11), time:'08:00', jobId:'j1', notes:'', created:now()}
  ];
  DB.changeOrders = [{id:'co1', jobId:'j1', number:'CO-001', title:'Add outdoor spigot', desc:'Add outdoor spigot', amount:420, status:'Draft', date:ds(7), created:now()}];
  DB.photos = [];
  const png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAF0lEQVR42mP8z8Dwn4EIwDiqkL4KAcT9GO0U4BxoAAAAAElFTkSuQmCC';
  for(let i=0;i<4;i++) DB.photos.push({id:'ph'+i, jobId:'j1', roomId:i<3?['r1','r2','r3'][i]:'', src:png, date:now(), caption:'', created:now()});
  DB.shopping = [{id:'s1', jobId:'j1', text:'3/4 inch copper elbows', qty:12, unit:'ea', price:2.5, store:'Ferguson', note:'', bought:false}];
  try{ _syncToken=''; }catch(e){}
  try{ renderAll(); }catch(e){}
})();
"""

async def make_page(b, w=390, h=844, zoom=1.15, base='http://localhost:8795/', page='index.html'):
    ctx = await b.new_context(viewport={'width':w,'height':h}, device_scale_factor=2, has_touch=True, is_mobile=(w<700))
    async def stub(route):
        u = route.request.url
        if 'api.github.com' in u:
            return await route.fulfill(status=200, content_type='application/json', body='{"id":"g1","owner":{"login":"stan"},"files":{}}')
        return await route.fulfill(status=200, body='{}')
    await ctx.route(re.compile(r'https://(?!localhost).*'), stub)
    pg = await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.goto(base+page); await pg.wait_for_timeout(1500)
    await pg.evaluate("var l=document.getElementById('bp-lock'); l&&l.remove()")
    await pg.evaluate(AUDIT_JS)
    await pg.evaluate(SEED_JS)
    await pg.evaluate(f"bpSetZoom({zoom})")
    return ctx, pg, errs

REPO = os.path.dirname(os.path.abspath(__file__))
SCREENS = [
 ('Home','s-home',"showScreen('s-home')"), ('Jobs','s-jobs',"showScreen('s-jobs')"),
 ('Estimates','s-jobs',"showScreen('s-jobs'); setJobsTab('estimates')"),
 ('Punch','s-punch',"showScreen('s-punch')"), ('Photos','s-photos',"showScreen('s-photos')"),
 ('Areas','s-rooms',"showScreen('s-rooms')"), ('Calendar','s-calendar',"showScreen('s-calendar')"),
 ('Search','s-search',"showScreen('s-search')"), ('Job detail','s-job-detail',"openJobDetail('j1')"),
 ('Room detail','s-room-detail',"openRoomDetail('r1')"),
]
FIN = ['overview','invoices','expenses','contractors','deliveries','permits','changeorders','spending']
SIZES = [(375,812),(390,844),(834,1194)]
ZOOMS = [1,1.15,1.3,1.45]
fails = []; checks = 0
def ok(cond, msg):
    global checks; checks += 1
    if not cond: fails.append(msg); print('  FAIL', msg)

async def layout(pg, tag):
    items = SCREENS + [('Money: '+t,'s-finance',"showScreen('s-finance'); setFinanceTab('%s')"%t) for t in FIN]
    for name,sid,js in items:
        await pg.evaluate("closeNavDrawer()"); await pg.evaluate(js); await pg.wait_for_timeout(250)
        await pg.evaluate(f"var s=document.getElementById('{sid}'); s&&(s.scrollTop=0)")
        r = await pg.evaluate(f"window.__audit('#{sid}', {{fab:false}})")
        await pg.evaluate(f"var s=document.getElementById('{sid}'); s&&(s.scrollTop=s.scrollHeight)"); await pg.wait_for_timeout(120)
        r2 = await pg.evaluate(f"window.__audit('#{sid}', {{fab:true}})")
        t = f'{tag} {name}'
        ok('error' not in r, t+' missing')
        if 'error' in r: continue
        ok(not r['overflowX'], f'{t} sideways overflow {r["overflowX"]}')
        ok(not r['offscreen'], f'{t} off screen {r["offscreen"][:2]}')
        ok(not r['overlap'], f'{t} overlap {r["overlap"][:2]}')
        ok(not r2['fab'], f'{t} dock/mic covers {r2["fab"][:2]}')

async def features(pg, tag):
    # Areas has a way home
    await pg.evaluate("showScreen('s-rooms')")
    ok(await pg.evaluate("!!document.querySelector('#s-rooms > .topbar .bp-burger')"), tag+' Areas has no menu button')
    # dock exists and is on the right half
    d = await pg.evaluate("(()=>{var e=document.getElementById('bp-dock'); if(!e) return null; var r=e.getBoundingClientRect(); return [r.left,r.right,innerWidth]})()")
    ok(d and d[0] > d[2]*0.3, tag+' dock missing or too far left')
    # menu opens the drawer, works from every main screen, and drawer gets you Home
    for sid,js in [('s-rooms',"showScreen('s-rooms')"),('s-finance',"showScreen('s-finance')"),('s-calendar',"showScreen('s-calendar')")]:
        await pg.evaluate(js); await pg.wait_for_timeout(150)
        await pg.evaluate("document.getElementById('bp-dock-menu').click()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("document.body.classList.contains('bp-drawer-open')"), f'{tag} dock Menu does not open drawer on {sid}')
        await pg.evaluate("closeNavDrawer()")
    # Back from Areas returns somewhere other than Areas
    await pg.evaluate("showScreen('s-home'); showScreen('s-rooms')"); await pg.wait_for_timeout(150)
    await pg.evaluate("document.getElementById('bp-dock-back').click()"); await pg.wait_for_timeout(250)
    ok(await pg.evaluate("!document.getElementById('s-rooms').classList.contains('active')"), tag+' Back does not leave Areas')
    # Finance filter sits on its own row below the title
    await pg.evaluate("showScreen('s-finance'); setFinanceTab('invoices')"); await pg.wait_for_timeout(200)
    await pg.evaluate("var s=document.getElementById('s-finance'); s.scrollTop=0; window.scrollTo(0,0)"); await pg.wait_for_timeout(150)
    g = await pg.evaluate("(()=>{var f=document.getElementById('finance-job-filter'),t=document.querySelector('#s-finance .topbar, #s-finance h1, #finance-sticky > div');var fr=f.getBoundingClientRect();var tt=[...document.querySelectorAll('#finance-sticky .topbar *')].filter(e=>!e.children.length&&e.offsetParent).map(e=>e.getBoundingClientRect());return {fTop:fr.top,fLeft:fr.left,fRight:fr.right,tBottom:Math.max(0,...tt.map(r=>r.bottom)),inRow:!!f.closest('#bp-fin-filter-row')}})()")
    ok(g['inRow'] and g['fTop'] >= g['tBottom']-1, f'{tag} Finance filter overlaps header {g}')

async def calendar(pg, tag):
    await pg.evaluate("showScreen('s-calendar')"); await pg.wait_for_timeout(200)
    cols = await pg.evaluate("(()=>{var n=new Date();var ev=getCalendarEvents(n.getFullYear(),n.getMonth());var m={};(Array.isArray(ev)?ev:Object.values(ev).flat()).forEach(e=>{m[e.kind||e.type]=e.color});return m})()")
    ok(cols.get('job-start','').lower()=='#30d158', f'{tag} Job Start not green: {cols.get("job-start")}')
    cats = await pg.evaluate("window.BP_CAL_COLORS||{}")
    import math
    def lab(h):
        h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
        f=lambda c: ((c+0.055)/1.055)**2.4 if c>0.04045 else c/12.92
        r,g,b=f(r),f(g),f(b); X=(r*.4124+g*.3576+b*.1805)/.95047; Y=r*.2126+g*.7152+b*.0722; Z=(r*.0193+g*.1192+b*.9505)/1.08883
        h2=lambda t: t**(1/3) if t>.008856 else 7.787*t+16/116
        return (116*h2(Y)-16, 500*(h2(X)-h2(Y)), 200*(h2(Y)-h2(Z)))
    uniq = {}
    for k,v in cats.items():
        if k in ('con-start','con-end'): continue          # con-start/con-end intentionally share the contractor color
        uniq[k]=v
    ks=list(uniq)
    ok(len(ks)>=8, tag+' too few calendar categories')
    for i in range(len(ks)):
        for j in range(i+1,len(ks)):
            a,b=lab(uniq[ks[i]]),lab(uniq[ks[j]]); de=math.dist(a,b)
            ok(de>=25, f'{tag} calendar colors too close {ks[i]}/{ks[j]} dE={de:.0f}')

async def taps(pg, tag):
    for sid,js in [('s-jobs',"showScreen('s-jobs')"),('s-punch',"showScreen('s-punch')"),('s-finance',"showScreen('s-finance'); setFinanceTab('invoices')"),('s-rooms',"showScreen('s-rooms')")]:
        await pg.evaluate(js); await pg.wait_for_timeout(350)
        n = await pg.evaluate(f"(()=>{{var z=parseFloat(getComputedStyle(document.body).zoom)||1;var bad=[];document.querySelectorAll('#{sid} .back-btn, #{sid} .topbar-btn, #bp-dock button').forEach(e=>{{if(!e.offsetParent&&e.id!='bp-dock-menu')return;var r=e.getBoundingClientRect();if(r.width&&Math.min(r.width,r.height)<43)bad.push(e.className+' '+Math.round(r.width)+'x'+Math.round(r.height))}});return bad}})()")
        ok(not n, f'{tag} {sid} small thumb targets {n}')

async def main():
    from playwright.async_api import async_playwright
    srv = subprocess.Popen(['python3','-m','http.server','8795','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for (w,h) in SIZES:
                for z in ZOOMS:
                    tag=f'[{w}x{h} zoom {z}]'; print(tag)
                    ctx,pg,errs = await make_page(b,w,h,z)
                    await layout(pg, tag)
                    if z in (1,1.45): await features(pg, tag); await taps(pg, tag)
                    if z==1: await calendar(pg, tag)
                    ok(not errs, f'{tag} JS errors {errs[:2]}')
                    await ctx.close()
            await b.close()
    finally: srv.terminate()
    print(f'\n{checks-len(fails)}/{checks} checks passed')
    sys.exit(1 if fails else 0)
asyncio.run(main())
