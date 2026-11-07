"""v6.9.13 — Spaces: ticking checklist items never throws the space back to the top (Command Center
on Mac/iPad), ticked items stay in view so you can keep checking, and Open / Complete are line icons
with counts (no words) in both apps.
Run from repo root: python3 test_v6913_space_ticks.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8913
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};Object.defineProperty(navigator,'maxTouchPoints',{get:function(){return 5;}});"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', startDate:'2026-10-01', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }];
 DB.punchlist = []; for (var i = 1; i <= 16; i++) DB.punchlist.push({ id:'p'+i, jobId:'j1', roomId:'r1', text:'Item number '+i, done:i>10, updatedAt:t });
 try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} } }"""
SEG = """(sel) => [].map.call(document.querySelectorAll(sel + ' button[data-bp-show]'), function(b){
  return { k: b.getAttribute('data-bp-show'), text: b.textContent.trim(), svg: !!b.querySelector('svg'), on: b.classList.contains('on'), label: b.getAttribute('aria-label'), color: getComputedStyle(b).color }; })"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def start(b, url, **kw):
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
    return ctx, pg, errs
async def cc(b, name, vp, ua=None):
    print('\n' + name)
    kw = {'viewport': vp}
    if ua: kw.update(user_agent=ua, has_touch=True)
    ctx, pg, errs = await start(b, 'desktop.html', **kw)
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 13), name + ': on v6.9.13 or newer')
    await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(600)
    s = await pg.evaluate(SEG, '#bp-mrd-seg')
    ok(len(s) == 2 and all(x['svg'] for x in s) and [x['text'] for x in s] == ['10', '6'], name + ': Open / Complete are icons + counts, no words ' + str([x['text'] for x in s]))
    ok(s[0]['label'] == 'Open 10' and s[1]['label'] == 'Complete 6', name + ': buttons still named for screen readers')
    ok(s[0]['on'] and s[0]['color'] == 'rgb(255, 69, 58)', name + ': Open (active) is red = open work ' + s[0]['color'])
    max_ = await pg.evaluate("(() => { var m = document.getElementById('modal-room-detail'); return m.scrollHeight - m.clientHeight; })()")
    want = min(150, max_)
    tops = []
    for k in range(5):
        await pg.evaluate("document.getElementById('modal-room-detail').scrollTop = %d" % want)
        await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-desk-checklist input[type=checkbox]'), function(c){ return !c.checked && c.offsetParent; })[0].click()")
        await pg.wait_for_timeout(450)
        tops.append(await pg.evaluate("document.getElementById('modal-room-detail').scrollTop"))
    ok(want > 0 and all(t == want for t in tops), name + ': 5 ticks in a row, window stays where it was (%d) %s' % (want, tops))
    vis = await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-desk-checklist input[type=checkbox]'), function(c){ return c.offsetParent; }).map(function(c){ return c.checked; })")
    ok(len(vis) == 10 and sum(vis) == 5, name + ': the 5 ticked items stay in view, ticked, so you can keep going ' + str(vis))
    s = await pg.evaluate(SEG, '#bp-mrd-seg')
    ok([x['text'] for x in s] == ['5', '11'], name + ': counts follow each tick ' + str([x['text'] for x in s]))
    await pg.click('#bp-mrd-seg button[data-bp-show="done"]'); await pg.wait_for_timeout(250)
    s = await pg.evaluate(SEG, '#bp-mrd-seg')
    ok(s[1]['on'] and s[1]['svg'] and s[1]['color'] == 'rgb(48, 209, 88)', name + ': Complete (active) is green, still an icon ' + s[1]['color'])
    await pg.screenshot(path='/tmp/claude-0/s/%s.png' % name.split()[0])
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def phone(b):
    name = 'iPhone'; print('\n' + name)
    ctx, pg, errs = await start(b, 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    s = await pg.evaluate(SEG, '#s-room-detail .bp-seg')
    ok(len(s) == 2 and all(x['svg'] for x in s) and [x['text'] for x in s] == ['10', '6'], name + ': Open / Complete are icons + counts ' + str([x['text'] for x in s]))
    await pg.evaluate("(function(){ var a = document.getElementById('s-room-detail'); a.scrollTop = 200; window.scrollTo(0, 200); })()")
    y0 = await pg.evaluate("[document.getElementById('s-room-detail').scrollTop, window.scrollY]")
    for k in range(4):
        await pg.evaluate("(function(){ var it = (DB.punchlist||[]).filter(function(n){ return n.roomId === 'r1' && !n.done; })[0]; toggleChecklistItem(it.id); })()")
        await pg.wait_for_timeout(400)
    await pg.wait_for_timeout(1600)   # the list redraws once, ~1s after the last tick
    y1 = await pg.evaluate("[document.getElementById('s-room-detail').scrollTop, window.scrollY]")
    ok(y0 == y1 and max(y0) > 0, name + ': page stays where it was through the ticks %s -> %s' % (y0, y1))
    s = await pg.evaluate(SEG, '#s-room-detail .bp-seg')
    ok([x['text'] for x in s] == ['6', '10'] and all(x['svg'] for x in s), name + ': 4 ticks in a row, counts follow, icons stay ' + str([x['text'] for x in s]))
    await pg.screenshot(path='/tmp/claude-0/s/iphone.png')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await cc(b, 'iPad Command Center', {'width': 1180, 'height': 820}, IPAD)
            await cc(b, 'Mac Command Center', {'width': 1440, 'height': 760})
            await phone(b)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
