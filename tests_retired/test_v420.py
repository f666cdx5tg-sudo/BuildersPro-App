"""v4.20 — Shopping List / Daily Log buttons must sit side by side with a clear gap,
and must STILL do so after a full-page job section is opened and closed."""
from playwright.sync_api import sync_playwright
import subprocess, time, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
srv = subprocess.Popen(['python3', '-m', 'http.server', '8775'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
ok = []
def chk(n, c): ok.append(bool(c)); print(('PASS ' if c else 'FAIL ') + n)
GEOM = """(function(){var jb=document.getElementById('bp-job-daily-bar');if(!jb)return null;var cs=getComputedStyle(jb);
 var k=[].map.call(jb.children,function(b){var r=b.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,r:r.right,b:r.bottom}});
 return {display:cs.display,k:k}})()"""
KIDS = "[].map.call(document.getElementById('s-job-detail').children,function(c){return (c.id||c.className||c.tagName)+'|'+c.style.display}).join(';')"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(viewport={'width': 390, 'height': 844}).new_page(); errs = []
    pg.on('pageerror', lambda x: errs.append(str(x)))
    pg.goto('http://localhost:8775/index.html'); pg.wait_for_timeout(2200)
    pg.evaluate("document.getElementById('bp-lock')?.remove()")
    chk('version 4.20', pg.evaluate('APP_VERSION') == '4.20')
    pg.evaluate("""(function(){DB.jobs=[{id:'j1',name:'Shedwick',client:'Courtney Benson',address:'634 N. Shedwick St',status:'Active',contractValue:500}];
      DB.rooms=[];DB.punchlist=[];DB.photos=[];(window.bpSave||save)();openJobDetail('j1');})()""")
    pg.wait_for_timeout(1200)
    def check(tag):
        g = pg.evaluate(GEOM)
        chk(tag + ': bar is a flex row', g and g['display'] == 'flex')
        k = g['k']
        chk(tag + ': 2 buttons side by side', len(k) == 2 and abs(k[0]['y'] - k[1]['y']) < 4)
        chk(tag + ': >=10px clear gap between them', len(k) == 2 and (k[1]['x'] - k[0]['r']) >= 10)
        chk(tag + ': equal width', len(k) == 2 and abs(k[0]['w'] - k[1]['w']) < 3)
        return g
    check('fresh job screen')
    before = pg.evaluate(KIDS)
    keys = pg.evaluate("[].map.call(document.querySelectorAll('#jd-stack .bp-acc'),function(a){return a.getAttribute('data-k')})")
    print('sections', keys)
    for key in (keys[:2] or ['spaces']):
        pg.evaluate("bpOpenJobSection('%s','j1')" % key); pg.wait_for_timeout(500)
        chk('section %s opens full page (other children hidden)' % key, pg.evaluate("getComputedStyle(document.getElementById('bp-job-daily-bar')).display") == 'none')
        pg.evaluate("bpCloseSectionFocus()"); pg.wait_for_timeout(400)
        check('after closing %s' % key)
    after = pg.evaluate(KIDS)
    # the focus bar is created on first use (hidden); everything else must be unchanged
    strip = lambda s: [x for x in s.split(';') if not x.startswith('jd-focus-bar')]
    print('diff:', [x for x in strip(after) if x not in strip(before)], [x for x in strip(before) if x not in strip(after)])
    chk('every screen child kept its own display after open/close', strip(before) == strip(after))
    pg.screenshot(path=OUT + '/v420_job.png')
    chk('no JS errors', not errs); print(errs)
    b.close()
print(sum(ok), '/', len(ok)); srv.kill(); sys.exit(0 if all(ok) else 1)
