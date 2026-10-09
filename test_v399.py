from playwright.sync_api import sync_playwright
fail=0
with sync_playwright() as p:
    b=p.chromium.launch()
    for u,vp,show in (('index.html',(390,844),"showScreen('s-job-detail');currentJobId='jH';renderJobDetail('jH');bpOpenJobSection('notes','jH')"),('desktop.html',(1440,900),"showView('job-detail');")):
        pg=b.new_page(viewport={'width':vp[0],'height':vp[1]}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://localhost:8799/'+u); pg.evaluate("document.getElementById('bp-lock')?.remove()")
        pg.evaluate("DB.jobs=[{id:'jH',name:'H',status:'active',homeInfo:{laundry:'Basement',attic:'None',chimneys:'1'}},{id:'jI',name:'I',status:'active',homeInfo:{laundry:'Basement'}}];window.currentJobId='jH'")
        pg.evaluate(show); pg.wait_for_timeout(2200)
        def st():
            return pg.evaluate("(()=>{var c=document.getElementById('bp-home-card');return c?[c.querySelectorAll('button').length,c.textContent.indexOf('Tap one')>=0]:null})()")
        s1=st()   # complete -> collapsed (1 button = hamburger, no 'Tap one')
        pg.evaluate("bpToggleHome('jH')"); pg.wait_for_timeout(200); s2=st()
        pg.evaluate("bpToggleHome('jH')"); pg.wait_for_timeout(200); s3=st()
        pg.evaluate("window.currentJobId='jI'"); pg.evaluate(show.replace('jH','jI').replace("bpOpenJobSection('notes','jI')","bpOpenJobSection('notes','jI')")); pg.wait_for_timeout(2200); s4=st()
        ok = s1==[1,False] and s2[1] and s3==[1,False] and s4 and s4[1] and not errs
        print(u,s1,s2,s3,s4,'PASS' if ok else 'FAIL',errs[:2]); fail+=not ok
    b.close()
raise SystemExit(fail)
