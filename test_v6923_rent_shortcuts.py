"""v6.9.23 — the page hands next month's (and the month after's) rent statements to the native app
for the Shortcuts action "Get Rent Statements", and takes back what Shortcuts already sent.
Run from repo root: python3 test_v6923_rent_shortcuts.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8923
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.__posts=[];window.BPShell={version:'t',caps:{ai:true,rentShortcuts:true}};window.webkit={messageHandlers:{bp:{postMessage:function(m){window.__posts.push(JSON.parse(JSON.stringify(m)));}}}};"
SEED = """() => { var t = new Date().toISOString(), d = new Date(), k = d.getFullYear() + '-' + ('0'+(d.getMonth()+1)).slice(-2);
 DB.jobs = DB.jobs.filter(function(j){ return !j.rental; }); DB.rooms = DB.rooms.filter(function(r){ return !r.unit; });
 DB.jobs.push({ id:'rp1', name:'12 Peach St', address:'12 Peach St', status:'Active', rental:true, created:t, payInfo:'Zelle to 201-555-0000' });
 DB.rooms.push({ id:'ru1', name:'Unit 2', jobId:'rp1', type:'Other', kind:'room', unit:true, created:t, tenant:{ name:'Anna Lee', phone:'(201) 555-0100', email:'anna@x.com', moveIn: k + '-01' }, rent:2100, dueDay:1, rentPays:[{ id:'p1', month:k, amount:2100, date:k+'-01', method:'Zelle' }], inventory:[] });
 DB.rooms.push({ id:'ru2', name:'Unit 3', jobId:'rp1', type:'Other', kind:'room', unit:true, created:t, tenant:{}, rent:'', inventory:[] });
 __posts.length = 0; bpRentPushNative(); }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, **kw):
    print('\n' + name)
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    ok(await pg.evaluate("APP_VERSION") in ('6.9.23','6.9.24'), name + ': on v6.9.23+')
    await pg.evaluate(SEED); await pg.wait_for_timeout(700)
    posts = await pg.evaluate("__posts.filter(function(m){ return m.kind === 'rentStatements'; })")
    ok(len(posts) == 1, name + ': statements handed to the native app')
    items = posts[-1]['items'] if posts else []
    nk = await pg.evaluate("(function(){ var d=new Date(); var a=new Date(d.getFullYear(), d.getMonth()+1, 1), b=new Date(d.getFullYear(), d.getMonth()+2, 1); function k(x){ return x.getFullYear()+'-'+('0'+(x.getMonth()+1)).slice(-2); } return [k(a), k(b)]; })()")
    ok([i['month'] for i in items] == nk, name + ': next month and the month after, occupied units only ' + str([i['month'] for i in items]))
    i0 = items[0] if items else {}
    ok(i0.get('phone') == '2015550100' and i0.get('email') == 'anna@x.com' and i0.get('tenant') == 'Anna Lee', name + ': phone digits, email, tenant')
    ok('RENT STATEMENT' in i0.get('body', '') and 'Zelle to 201-555-0000' in i0.get('body', '') and i0.get('subject', '').startswith('Rent statement'), name + ': message body + subject')
    # a change in Rentals re-sends
    await pg.evaluate("__posts.length = 0; var u = DB.rooms.find(function(r){ return r.id==='ru1'; }); u.rent = 2200; bpRentOpen('ru1'); document.querySelector('#bp-rent [data-a=\"tenant\"]').click(); document.querySelector('.bp20-ov .bp20-go').click();")
    await pg.wait_for_timeout(700)
    posts = await pg.evaluate("__posts.filter(function(m){ return m.kind === 'rentStatements'; })")
    ok(len(posts) >= 1 and '$2,200.00' in posts[-1]['items'][0]['body'], name + ': editing a tenant updates the statements')
    # what Shortcuts sent comes back
    await pg.evaluate("bpRentNativeSent({ 'ru1|%s': '2026-11-25' })" % nk[0]); await pg.wait_for_timeout(200)
    s = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).stmtSent")
    ok(s and s.get(nk[0], {}).get('how') == 'Shortcuts', name + ': sent by Shortcuts shows as sent in the app')
    # no native bridge → nothing posted, no error
    await pg.evaluate("__posts.length = 0; BPShell.caps.rentShortcuts = false; bpRentPushNative()"); await pg.wait_for_timeout(600)
    ok(await pg.evaluate("__posts.length") == 0, name + ': old native app (no Shortcuts support) gets nothing')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'Mac Command Center', 'desktop.html', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
