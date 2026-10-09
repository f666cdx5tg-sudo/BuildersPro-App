from playwright.sync_api import sync_playwright
seed="""()=>{DB.jobs=DB.jobs||[];DB.expenses=[];DB.recycle=[];DB.tombstones={};
for(var i=0;i<5;i++){DB.recycle.push({id:'rc'+i,coll:'expenses',rec:{id:'e'+i,desc:'x'+i},label:'Item '+i,deletedAt:new Date().toISOString()});}
DB.tombstones['expenses:old1']=new Date().toISOString();DB.tombstones['expenses:old2']=new Date().toISOString();bpRenderRecycle();}"""
fail=0
with sync_playwright() as p:
    b=p.chromium.launch()
    for u,vp in (('desktop.html',(1440,900)),('index.html',(390,844))):
        pg=b.new_page(viewport={'width':vp[0],'height':vp[1]}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
        pg.goto('http://localhost:8799/'+u); pg.evaluate("document.getElementById('bp-lock')?.remove()")
        if u=='index.html': pg.evaluate("document.getElementById('recycle-wrap')||document.body.insertAdjacentHTML('beforeend','<div id=recycle-wrap></div>')")
        pg.evaluate(seed); pg.wait_for_timeout(200)
        cbs=pg.evaluate("document.querySelectorAll('#recycle-wrap .bp-rec-cb').length")
        pg.evaluate("document.getElementById('bp-rec-all').click()")
        sel=pg.evaluate("document.querySelectorAll('#recycle-wrap .bp-rec-cb:checked').length")
        pg.evaluate("bpRecBulkRestore()"); pg.wait_for_timeout(200)
        restored=pg.evaluate("[DB.expenses.length, DB.recycle.length]")
        pg.evaluate(seed); pg.evaluate("document.getElementById('bp-rec-all').click()"); pg.evaluate("bpRecBulkPurge()")
        purged=pg.evaluate("[DB.expenses.length, DB.recycle.length]")
        has_clr=pg.evaluate("!!document.getElementById('bp-rec-clrall')")
        ok = cbs==5 and sel==5 and restored==[5,0] and purged==[0,0] and has_clr and not errs
        print(u,cbs,sel,restored,purged,has_clr,'PASS' if ok else 'FAIL',errs[:2]); fail+=not ok
    b.close()
raise SystemExit(fail)
