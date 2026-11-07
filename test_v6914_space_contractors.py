"""v6.9.14 — In a space: Contractors rows = dropdown (whole phone book) + value + scope of work.
A sub's job contract = the total of his space values (Stan chose A). Picking a phone-book sub
who isn't on the job adds him to the job. A sub with a typed-in job contract is only switched
over after the app asks. iPhone field app, iPad and Mac Command Center.
Run from repo root: python3 test_v6914_space_contractors.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8914
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};Object.defineProperty(navigator,'maxTouchPoints',{get:function(){return 5;}});"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'N. Peach St', client:'A', address:'1 St', status:'Active', contractValue:50000, startDate:'2026-10-01', updatedAt:t },
            { id:'j2', name:'Elm Ave', client:'B', address:'2 St', status:'Active', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Bath', type:'Bathroom', updatedAt:t }, { id:'r2', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t },
             { id:'r3', jobId:'j1', name:'Hall', type:'Other', contractorIds:['cJoe'], updatedAt:t }];
 DB.contacts = [{ id:'bMike', type:'Contractor', name:'Mike Rossi', company:"Mike's Plumbing", phone:'2015550100', skills:['Plumbing'] }];
 DB.contractors = [{ id:'cSal', jobId:'j2', name:'Sal Electric', trade:'Electrical', value:9000, scope:'', status:'Active' },
                   { id:'cJoe', jobId:'j1', name:'Joe Tile', trade:'Tile', value:10000, scope:'', status:'Active' }];
 DB.punchlist = []; for (var i = 1; i <= 14; i++) DB.punchlist.push({ id:'p'+i, jobId:'j1', roomId:'r1', text:'Item '+i, done:false, updatedAt:t });
 try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){ try { save(); } catch(e3){} } } }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, **kw):
    print('\n' + name)
    mac = 'desktop' in url
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    answers = []
    async def dlg(d):
        await (d.accept() if (answers.pop(0) if answers else True) else d.dismiss())
    pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
    ok(await pg.evaluate("APP_VERSION") == '6.9.14', name + ': on v6.9.14')
    host = '#modal-room-detail' if mac else '#s-room-detail'
    await pg.evaluate(SEED); await pg.wait_for_timeout(300)
    async def open_room(rid):
        await pg.evaluate("openRoomDetail('%s')" % rid); await pg.wait_for_timeout(500)
    async def val(sel_idx, v):
        loc = pg.locator(host + ' .bp-ssub-row').nth(sel_idx).locator('.bp-ssub-v')
        await loc.fill(v); await loc.press('Tab'); await pg.wait_for_timeout(250)
    con = lambda cid: pg.evaluate("(function(){ var c = (DB.contractors||[]).find(function(x){ return x.id === '%s'; }); return c ? +c.value : null; })()" % cid)
    mike = "(function(){ return (DB.contractors||[]).filter(function(c){ return c.jobId === 'j1' && /mike/i.test(c.name + ' ' + (c.contact||'')); }); })()"

    await open_room('r1')
    ok('No contractors in this space yet' in await pg.inner_text(host + ' .bp-ssub'), name + ': empty space says so, + Add is right there')
    await pg.click(host + ' .bp-ssub-add'); await pg.wait_for_timeout(250)
    MIKE = "Mike's Plumbing — Mike Rossi" if mac else "Mike's Plumbing"
    opts = await pg.evaluate("[].map.call(document.querySelectorAll('%s .bp-ssub-row select option'), function(o){ return o.textContent; })" % host)
    ok(MIKE in opts and 'Sal Electric' in opts and 'Joe Tile' in opts, name + ': dropdown = whole phone book + subs on other jobs ' + str(opts))
    ok(opts[0] == 'Choose contractor' and opts[-1] == 'Remove from this space', name + ': first line asks, last line removes')
    await pg.select_option(host + ' .bp-ssub-row select', label=MIKE); await pg.wait_for_timeout(250)
    m = await pg.evaluate(mike)
    ok(len(m) == 1 and m[0]['fromSpaces'] and m[0]['contact'] == 'Mike Rossi', name + ': picking Mike adds him to this job automatically')
    await val(0, '4500')
    ok(await con(m[0]['id']) == 4500, name + ': Bath $4,500 → his job contract $4,500')
    sc = pg.locator(host + ' .bp-ssub-row').nth(0).locator('.bp-ssub-s')
    await sc.fill('Rough-in + set fixtures'); await sc.press('Tab'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("DB.rooms.find(function(r){ return r.id === 'r1'; }).subs[0].scope") == 'Rough-in + set fixtures', name + ': scope of work saved on the space')
    ok('$4,500.00' in await pg.inner_text(host), name + ': space shows its contractor total to the penny')
    if mac:   # a tick redraws the whole window — the rows must come back intact
        await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-desk-checklist input[type=checkbox]'), function(c){ return !c.checked && c.offsetParent; })[0].click()"); await pg.wait_for_timeout(450)
        ok(await pg.input_value(host + ' .bp-ssub-v') == '4500.00' and await pg.input_value(host + ' .bp-ssub-s') == 'Rough-in + set fixtures', name + ': a checklist tick keeps the contractor rows')

    await open_room('r2')
    await pg.click(host + ' .bp-ssub-add'); await pg.wait_for_timeout(200)
    await pg.select_option(host + ' .bp-ssub-row select', label=MIKE); await pg.wait_for_timeout(200)
    await val(0, '3,000')
    m2 = await pg.evaluate(mike)
    ok(len(m2) == 1 and await con(m2[0]['id']) == 7500, name + ': Kitchen $3,000 → still ONE Mike on the job, contract $7,500')
    await pg.click(host + ' .bp-ssub-add'); await pg.wait_for_timeout(200)
    await pg.locator(host + ' .bp-ssub-row').nth(1).locator('select').select_option(label=MIKE); await pg.wait_for_timeout(200)
    ok(len(await pg.evaluate("DB.rooms.find(function(r){ return r.id === 'r2'; }).subs.filter(function(s){ return s.conId; })")) == 1, name + ': same sub twice in one space is refused')
    await pg.locator(host + ' .bp-ssub-row').nth(1).locator('select').select_option(value='__rm'); await pg.wait_for_timeout(200)

    await open_room('r3')
    ok(await pg.locator(host + ' .bp-ssub-row').count() == 1 and 'Joe Tile' in await pg.evaluate("(function(){ var s = document.querySelector('%s .bp-ssub-row select'); return s.options[s.selectedIndex].text; })()" % host), name + ': older checkbox pick shows as a row (no value yet)')
    answers.append(False); await val(0, '2000')
    ok(await con('cJoe') == 10000, name + ': Joe had a typed $10,000 contract — Cancel keeps it')
    ok(await pg.input_value(host + ' .bp-ssub-v') == '', name + ': …and the space value is not saved')
    answers.append(True); await val(0, '2000')
    ok(await con('cJoe') == 2000, name + ': OK switches Joe to the total of his space values ($2,000)')
    ok(await con('cSal') == 9000, name + ': other jobs untouched')

    await open_room('r2')
    await pg.select_option(host + ' .bp-ssub-row select', value='__rm'); await pg.wait_for_timeout(250)
    ok(await con(m2[0]['id']) == 4500, name + ': removing Mike from Kitchen → his contract drops back to $4,500')
    tot = await pg.evaluate("(DB.contractors||[]).filter(function(c){ return c.jobId === 'j1'; }).reduce(function(s, c){ return s + (+c.value||0); }, 0)")
    ok(tot == 6500, name + ': job subs total = $4,500 Mike + $2,000 Joe = $6,500 (what Money Left subtracts) → %s' % tot)
    await open_room('r1')
    await pg.screenshot(path='/tmp/claude-0/s/sub-%s.png' % name.split()[0])
    if not mac:
        await pg.evaluate("document.querySelector('#s-room-detail .bp-ssub').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("(function(){ var s = document.querySelector('#s-room-detail .bp-ssub-row select'); var c = document.createElement('canvas').getContext('2d'); var cs = getComputedStyle(s); c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily; return c.measureText(s.options[s.selectedIndex].text).width <= s.clientWidth - 26; })()"), name + ': the whole contractor name fits (not cut off)')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'iPad Command Center', 'desktop.html', viewport={'width': 1180, 'height': 820}, user_agent=IPAD, has_touch=True)
            await run(b, 'Mac Command Center', 'desktop.html', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
