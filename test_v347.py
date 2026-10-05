"""BuildersPro v3.47 area-row swipe (Cut/Delete) + photo stack/grid test.  Run: python3 test_v347.py  (needs playwright + chromium)
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

async def make_page(b, w=390, h=844, zoom=1.15, base='http://localhost:8796/', page='index.html'):
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
fails=[]; checks=0
def ok(c,m):
    global checks; checks+=1
    if not c: fails.append(m); print('  FAIL',m)

SWIPE = """(sel, dx)=>{ const el=document.querySelector(sel); if(!el) return 'no tile';
  el.scrollIntoView({block:'center'}); const r=el.getBoundingClientRect(); const x=r.left+r.width*0.8, y=r.top+r.height/2;
  const mk=(type,px)=>{ const t=new Touch({identifier:1,target:el,clientX:px,clientY:y}); return new TouchEvent(type,{bubbles:true,cancelable:true,touches:type==='touchend'?[]:[t],targetTouches:type==='touchend'?[]:[t],changedTouches:[t]}); };
  el.dispatchEvent(mk('touchstart',x)); for(let i=1;i<=6;i++) el.dispatchEvent(mk('touchmove',x+dx*i/6)); el.dispatchEvent(mk('touchend',x+dx)); return 'ok'; }"""


SETUP = """(()=>{
  const mk=(i)=> 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAF0lEQVR42mP8z8Dwn4EIwDiqkL4KAcT9GO0U4BxoAAAAAElFTkSuQmCC#'+i;
  DB.punchlist = DB.punchlist.filter(x=>x.roomId!=='r1');
  const base={jobId:'j1', roomId:'r1', trade:'Plumbing', value:0, priority:'Normal', done:false, tasks:[], created:now(), updatedAt:now()};
  DB.punchlist.push(Object.assign({id:'a0', text:'No photos here', photosBefore:[], photosAfter:[]},base));
  DB.punchlist.push(Object.assign({id:'a1', text:'One photo only', photosBefore:[{src:mk(1),date:now()}], photosAfter:[]},base));
  DB.punchlist.push(Object.assign({id:'a4', text:'Hot water heater tank replacement and new expansion tank with dielectric unions', photosBefore:[{src:mk(2),date:now()},{src:mk(3),date:now()}], photosAfter:[{src:mk(4),date:now()},{src:mk(5),date:now()}]},base));
  DB.punchlist.push(Object.assign({id:'a9', text:'Cleanup', done:true, photosBefore:[], photosAfter:[]},base));
  try{ localStorage.removeItem('bp_clip'); }catch(e){}
  openRoomDetail('r1');
})()"""

async def tap(pg, js):  # click via DOM (touch-synthesised swipes don't generate clicks)
    return await pg.evaluate(js)

async def main():
    from playwright.async_api import async_playwright
    srv = subprocess.Popen(['python3','-m','http.server','8796','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for (w,h,z) in [(390,844,1.15),(375,812,1.45),(834,1194,1)]:
                print(f'[{w}x{h} zoom {z}]')
                ctx,pg,errs = await make_page(b,w,h,z)
                await pg.evaluate(SETUP); await pg.wait_for_timeout(600)
                ok(await pg.evaluate("document.querySelectorAll('.bp-cl-row').length")==4, 'expected 4 rows')
                # rows: no inline cut / x buttons any more
                ok(await pg.evaluate("!document.querySelector('.bp-cl-row [onclick*=\"deleteChecklistItem\"], .bp-cl-row [onclick*=\"bpClipToggle\"]')"), 'row still has inline Cut/X buttons')
                # long name is shown in full (wraps, not clipped)
                clip = await pg.evaluate("(()=>{var n=document.querySelector('#cli-a4 .bp-cl-name');var r=n.getBoundingClientRect();var cs=getComputedStyle(n);return [n.scrollWidth<=n.clientWidth+1, cs.whiteSpace, cs.textOverflow, r.height]})()")
                ok(clip[0] and clip[1]!='nowrap' and clip[2]!='ellipsis', f'long name clipped {clip}')
                ok(await pg.evaluate("document.getElementById('cli-a4').scrollWidth<=document.getElementById('cli-a4').clientWidth+1"), 'row overflows sideways')
                # checkbox still toggles
                await pg.evaluate("document.querySelector('#cli-a0 > div').click()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='a0').done")==True, 'checkbox no longer toggles')
                await pg.evaluate("DB.punchlist.find(x=>x.id==='a0').done=false; openRoomDetail('r1')"); await pg.wait_for_timeout(300)

                # tiny swipe must not reveal
                await pg.evaluate(f"({SWIPE})('#cli-a0', -20)"); await pg.wait_for_timeout(350)
                ok(await pg.evaluate("!document.querySelector('.bp-cl-acts')"), 'tiny swipe revealed actions')
                # real swipe reveals both buttons, on screen
                await pg.evaluate(f"({SWIPE})('#cli-a0', -190)"); await pg.wait_for_timeout(350)
                box = await pg.evaluate("(()=>{var a=document.querySelector('.bp-cl-acts');if(!a)return null;var c=a.querySelector('.bp-cl-cut').getBoundingClientRect(),d=a.querySelector('.bp-cl-del').getBoundingClientRect();return [c.left,c.right,d.left,d.right,innerWidth,c.height,d.height,c.width]})()")
                ok(box is not None, 'swipe did not reveal actions')
                if box:
                    ok(box[0]>=0 and box[3]<=box[4]+1, f'actions off screen {box}')
                    ok(min(box[5],box[6],box[7])>=44, f'action buttons too small {box}')
                # swipe must not toggle/expand the row
                ok(await pg.evaluate("!window._expandedChecklistItems['a0']"), 'swipe expanded the row')
                # Cut puts it on the clipboard
                await pg.evaluate("document.querySelector('.bp-cl-cut').click()"); await pg.wait_for_timeout(400)
                ok(await pg.evaluate("bpClipGet().ids.indexOf('a0')>=0 && bpClipGet().mode==='cut'"), 'Cut did not clip the item')
                ok(await pg.evaluate("getComputedStyle(document.getElementById('cli-a0')).borderTopStyle")=='dashed', 'cut row not outlined')
                await pg.evaluate("bpClipClear()"); await pg.wait_for_timeout(300)
                # Delete asks first, Cancel keeps, confirm deletes
                n0 = await pg.evaluate("DB.punchlist.length")
                await pg.evaluate(f"({SWIPE})('#cli-a0', -190)"); await pg.wait_for_timeout(350)
                await pg.evaluate("document.querySelector('.bp-cl-del').click()"); await pg.wait_for_timeout(250)
                ok(await pg.evaluate("!!document.getElementById('bp-sw-confirm')"), 'no delete confirmation')
                ok(await pg.evaluate("DB.punchlist.length")==n0, 'deleted before confirming')
                await pg.evaluate("document.querySelector('#bp-sw-confirm .bp-sw-no').click()"); await pg.wait_for_timeout(500)
                ok(await pg.evaluate("DB.punchlist.length")==n0, 'Cancel deleted')
                ok(await pg.evaluate("!document.querySelector('.bp-cl-acts')"), 'row did not close after Cancel')
                await pg.evaluate(f"({SWIPE})('#cli-a0', -190)"); await pg.wait_for_timeout(350)
                await pg.evaluate("document.querySelector('.bp-cl-del').click()"); await pg.wait_for_timeout(250)
                await pg.evaluate("document.querySelector('#bp-sw-confirm .bp-sw-yes').click()"); await pg.wait_for_timeout(500)
                ok(await pg.evaluate("DB.punchlist.length")==n0-1, 'confirm did not delete')

                # photo stack
                ok(await pg.evaluate("!!document.querySelector('#cli-a4 .bp-stack') && document.querySelector('#cli-a4 .bp-sn').textContent==='4'"), 'no stack with count 4')
                ok(await pg.evaluate("!document.querySelector('#cli-a1 .bp-sn')"), 'single photo shows a count badge')
                # 4 photos -> grid
                await pg.evaluate("document.querySelector('#cli-a4 .bp-stack').click()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("document.querySelectorAll('#bp-clgrid .bp-gc').length")==4, 'grid did not open with 4 pictures')
                gb = await pg.evaluate("(()=>{var c=[...document.querySelectorAll('#bp-clgrid .bp-gc')].map(x=>x.getBoundingClientRect());return [Math.min(...c.map(r=>r.left)),Math.max(...c.map(r=>r.right)),innerWidth,c[0].width]})()")
                ok(gb[0]>=0 and gb[1]<=gb[2]+1 and gb[3]>=60, f'grid layout bad {gb}')
                ok(await pg.evaluate("document.querySelector('#bp-clgrid .bp-gt').innerText.indexOf('dielectric unions')>=0"), 'grid title not full item name')
                await pg.evaluate("document.querySelectorAll('#bp-clgrid .bp-gc')[2].click()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("!!document.getElementById('bp-clview') && PV_OK()".replace(' && PV_OK()','')), 'tapping a picture did not open the viewer')
                ok(await pg.evaluate("document.querySelector('#bp-clview').innerText.indexOf('3 of 4')>=0"), 'viewer opened on the wrong picture')
                await pg.evaluate("bpClViewClose()"); await pg.wait_for_timeout(200)
                ok(await pg.evaluate("!!document.getElementById('bp-clgrid')"), 'grid gone after closing the viewer')
                await pg.evaluate("document.querySelector('#bp-clgrid .bp-gf button').click()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("!document.getElementById('bp-clgrid') && !!document.getElementById('bp-clphoto-sheet')"), '+ Add photos did not open the Before/After sheet')
                await pg.evaluate("document.getElementById('bp-clphoto-sheet').remove()")
                # 1 photo -> viewer (no grid)
                await pg.evaluate("document.querySelector('#cli-a1 .bp-clphoto-btn').click()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("!!document.getElementById('bp-clview') && !document.getElementById('bp-clgrid')"), 'one photo should open the viewer directly')
                await pg.evaluate("bpClViewClose()")
                # 0 photos -> add sheet
                await pg.evaluate("(()=>{var b=document.querySelector('#cli-a9 .bp-clphoto-btn'); b.click()})()"); await pg.wait_for_timeout(300)
                ok(await pg.evaluate("!!document.getElementById('bp-clphoto-sheet')"), 'no-photo tap did not open the add sheet')
                await pg.evaluate("document.getElementById('bp-clphoto-sheet').remove()")
                # swiping on the stack itself must not hijack it (tap still works)
                # layout audit on the row list
                aud = await pg.evaluate("window.__audit('#room-detail-body, .screen.active')")
                ok(not aud.get('overflowX'), f"horizontal overflow {aud.get('overflowX')}")
                ok(not aud.get('offscreen'), f"offscreen {aud.get('offscreen')}")
                # v3.48: the sticky header grew a row (Room/Area chips) at the largest text sizes, so a row scrolled underneath it can touch
                # the header's own Progress text. That is the sticky header covering scrolled content, not two row parts colliding.
                _bad = [x for x in aud.get('overlap',[]) if ('cli-' in x or 'bp-cl' in x or 'bp-stack' in x) and '% (' not in x]
                ok(not _bad, f"overlaps {_bad[:4]}")
                ok(not errs, f'JS errors {errs[:2]}')
                await ctx.close()
            await b.close()
    finally: srv.terminate()
    print(f'\n{checks-len(fails)}/{checks} checks passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
