import re,sys
from playwright.sync_api import sync_playwright
t=open('test_command_center_icons.py').read()
SEED=re.search(r'SEED = """(.*?)"""',t,re.S).group(1)
SP=eval(re.search(r'SPACES = (\[.*?\])\nTYPES',t,re.S).group(1)); TY=eval(re.search(r'TYPES = (\[.*?\])\n',t,re.S).group(1))
with sync_playwright() as p:
    b=p.chromium.launch()
    for vp,z in (((390,844),1),((820,1180),1.4),((820,1180),1)):
        pg=b.new_page(viewport={'width':vp[0],'height':vp[1]}); pg.goto('http://localhost:8799/index.html'); pg.evaluate("document.getElementById('bp-lock')?.remove()")
        pg.evaluate(SEED,[SP,TY]); pg.evaluate("document.body.style.zoom=%s"%z)
        pg.evaluate("showScreen('s-job-detail');currentJobId='jobT';renderJobDetail('jobT');bpOpenJobSection('spaces','jobT')"); pg.wait_for_timeout(1500)
        r=pg.evaluate("""(()=>{var e=document.getElementById('jd-stack');var cs=getComputedStyle(e);var r=e.getBoundingClientRect();
          var before=e.scrollTop;e.scrollTop=500;var after=e.scrollTop;
          return {pos:cs.position,ovy:cs.overflowY,h:r.height,top:r.top,bottom:r.bottom,vh:innerHeight,sh:e.scrollHeight,ch:e.clientHeight,scrolled:after-before}})()""")
        print(vp,z,r)
    b.close()
