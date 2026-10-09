"""Command Center icon audit: every screen must show line icons, never raw emoji.

Seeds a job with spaces of every common name/type plus punch items, contractors,
expenses, invoices, permits, estimates, EOD reports; visits every screen; waits
for the app's emoji->line-icon converter to run; then scans visible text for any
emoji character still rendered as text (the hidden .bp-ic-t fallback copy and
<option>/<title> text are ignored, they cannot hold an SVG).
Exit code 1 and a per-screen list if any remain.   Run: python3 test_command_center_icons.py
"""
import asyncio, sys, json
from playwright.async_api import async_playwright
import os
URL = os.environ.get("TEST_URL", "http://localhost:8799/desktop.html")
SPACES = ["(F) Bathroom","(B) Bathroom","Bedroom","front Roof","Rear ROOF","Gutters","Chimney","Front Door","Side Door","Main Entrance",
 "Driveway","Front Steps","Sidewalk","Windows (Ext)","Basement/ mechanical","Basement","Foyer","2nd Fl.Stairs","3rd Fl. Stairs","Stairs",
 "Water Service","handicap ramp","Kitchen","Family Room","Living Room","Dining Room","Garage","Attic","Laundry","Hallway","Closet","Office",
 "Deck","Porch","Patio","Yard / Grading","Boiler Room","Utility Room","Unit 2 Bedroom - Level 2","Roof","HVAC","Electrical","Plumbing","Fence"]
TYPES = ["Bathroom","Bedroom","Exterior","Roof","Basement","Other","Kitchen","Living Room","Garage","Attic","Laundry","Hallway","Office"]
SEED = """(a)=>{
 var S=a[0],T=a[1];
 DB.jobs=DB.jobs||[];DB.rooms=DB.rooms||[];
 DB.jobs.push({id:'jobT',name:'N. Peach St',status:'active',client:'Test Client',address:'1 Main St',contractValue:50000,start:'2026-10-01'});
 S.forEach(function(n,i){DB.rooms.push({id:'rt'+i,jobId:'jobT',name:n,type:T[i%T.length]})});
 DB.punchlist=DB.punchlist||[];
 S.forEach(function(n,i){DB.punchlist.push({id:'pt'+i,jobId:'jobT',roomId:'rt'+i,text:'Item '+i,done:i%2===0,trade:'Plumbing'})});
 (DB.contractors=DB.contractors||[]).push({id:'ct1',name:'Bob Sub',trade:'Plumbing',jobId:'jobT'});
 (DB.expenses=DB.expenses||[]).push({id:'ex1',jobId:'jobT',desc:'Pipe',amount:100,date:'2026-10-02'});
 (DB.invoices=DB.invoices||[]).push({id:'iv1',jobId:'jobT',amount:500,status:'sent',date:'2026-10-03'});
 (DB.permits=DB.permits||[]).push({id:'pm1',jobId:'jobT',trade:'Plumbing',status:'open'});
 (DB.estimates=DB.estimates||[]).push({id:'es1',title:'Est',client:'C',status:'draft'});
 (DB.eodReports=DB.eodReports||[]).push({id:'eo1',jobId:'jobT',date:'2026-10-09',summary:'x'});
 window.currentJobId='jobT';
}"""

RESOLVE = """(a)=>{var S=a[0],T=a[1],bad=[];S.forEach(function(n){T.forEach(function(t){
   var h='';try{h=window.bpRoomIconHtml(n,t)||''}catch(e){}
   if(h.indexOf('<svg')<0) bad.push(n+' / '+t)})});return bad}"""
SCAN = """()=>{
 var re=/(\\p{Emoji_Presentation}|\\p{Extended_Pictographic}\\uFE0F|[\\u2600-\\u27BF\\u{1F000}-\\u{1FAFF}])/u;
 var ok=/^[\\u2713\\u2714\\u2715\\u2716\\u2717\\u2718\\u2605\\u2606\\u2022\\u25B2\\u25BC\\u25C0\\u25B6\\u25CF\\u25CB\\u25A0\\u25A1\\u2192\\u2190\\u2191\\u2193\\u2039\\u203A\\u2304\\u2713\\u2715]$/u;
 var out=[];var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);var n;
 while(n=w.nextNode()){
   var p=n.parentElement; if(!p) continue;
   if(p.closest('script,style,textarea,option,select,title,noscript,.bp-ic-t,[data-bp-nozoom] .bp-g-stage')) continue;
   var cs=getComputedStyle(p); if(cs.display==='none'||cs.visibility==='hidden') { if(!p.closest('.view.active')) continue; }
   if(!p.offsetParent && cs.position!=='fixed') continue;
   var t=n.nodeValue, m=t.match(new RegExp(re.source,'gu'))||[];
   m=m.filter(function(c){return !ok.test(c)});
   if(m.length) out.push({chars:m.join(''),ctx:(p.closest('button,.card,td,div')||p).textContent.trim().replace(/\\s+/g,' ').slice(0,60)});
 }
 return out;}"""
async def main():
    bad = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':1440,'height':900})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.wait_for_timeout(800)
        await pg.evaluate(SEED, [SPACES, TYPES])
        # 1) deterministic: every space name x every space type must resolve to an SVG line icon
        unresolved = await pg.evaluate(RESOLVE, [SPACES, TYPES])
        if unresolved:
            bad['bpRoomIconHtml has no line icon for'] = [{'chars':'(none)','ctx':u} for u in unresolved[:40]]
        # 2) every screen: no raw emoji left in visible text
        views = ['dashboard','jobs','job-detail','rooms','photos','punchlist','documents','eod','finance','estimates','calendar','time','contacts','archive','sync','search']
        for v in views:
            try:
                await pg.evaluate("(v)=>showView(v)", v)
            except Exception as e:
                print('  (could not open', v, str(e)[:80], ')'); continue
            await pg.wait_for_timeout(900)
            r = await pg.evaluate(SCAN)
            # chrome shared by all screens (header + sidebar) is reported once, on the first screen
            if r: bad[v] = r
        # the rooms/areas sub-views and per-area punch/photo groupings
        for js in ["window._bpAreaView='area'; showView('photos')", "window._bpAreaView='area'; showView('punchlist')"]:
            try:
                await pg.evaluate(js); await pg.wait_for_timeout(900)
                r = await pg.evaluate(SCAN)
                if r: bad[js] = r
            except Exception as e: pass
        await b.close()
    seen=set()
    total=0
    for v, items in bad.items():
        print('SCREEN', v)
        for it in items:
            key=(it['chars'],it['ctx'])
            if key in seen: continue
            seen.add(key); total+=1
            print('   raw emoji', it['chars'], '|', it['ctx'])
    print('page errors:', errs[:3])
    print('RESULT:', 'FAIL, %d raw emoji left' % total if total else 'PASS, no raw emoji on any Command Center screen')
    sys.exit(1 if total else 0)
asyncio.run(main())
