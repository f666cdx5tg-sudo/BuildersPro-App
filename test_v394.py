from playwright.sync_api import sync_playwright
seed="""()=>{DB.jobs=[{id:'jA',name:'Job A'},{id:'jB',name:'Job B'}];DB.documents=[{id:'d1',jobId:'jA',name:'Old',category:'Other',fileSrc:'data:text/plain;base64,aGk=',fileName:'a.txt',fileType:'text/plain',notes:'n',created:new Date().toISOString()}];}"""
fail=0
with sync_playwright() as p:
    b=p.chromium.launch()
    for u,vp in (('desktop.html',(1440,900)),('index.html',(390,844))):
        pg=b.new_page(viewport={'width':vp[0],'height':vp[1]}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://localhost:8799/'+u); pg.evaluate("document.getElementById('bp-lock')?.remove()"); pg.evaluate(seed)
        if u=='desktop.html':
            pg.evaluate("renderDesktopDocuments()")
        else:
            pg.evaluate("showScreen('s-job-detail');currentJobId='jA';renderJobDetail('jA')")
        pg.wait_for_timeout(300)
        n=pg.evaluate("document.querySelectorAll('.bp-doc-edit-btn').length")
        pg.evaluate("bpEditDoc('d1')"); pg.fill('#bpde-name','New name'); pg.select_option('#bpde-cat','Contract'); pg.select_option('#bpde-job','jB'); pg.fill('#bpde-notes','changed')
        pg.click('#bpde-save'); pg.wait_for_timeout(300)
        d=pg.evaluate("DB.documents[0]"); ok = n>=1 and d['name']=='New name' and d['category']=='Contract' and d['jobId']=='jB' and d['notes']=='changed' and d['fileSrc'].startswith('data:') and not errs and not pg.query_selector('#bp-doc-edit')
        print(u,'buttons',n,d['name'],d['jobId'],'PASS' if ok else 'FAIL',errs[:2]); fail+=not ok
    b.close()
raise SystemExit(fail)
