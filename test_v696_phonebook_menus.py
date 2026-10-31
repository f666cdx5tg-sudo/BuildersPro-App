"""v6.9.6 — phone book: one ≡ list menu (Contractors & subs · Clients), a search ICON with options
(All · Name · Company/Address · Cell · Email), skills in a ••• menu. iPhone and Mac.
Run from repo root: python3 test_v696_phonebook_menus.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8996
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs = [{id:'j1',name:'N. Peach St',status:'Active',client:'Shelden Washington',clientPhone:'8626869866',clientEmail:'hrlm2philly@gmail.com',address:'1536 N. Peach St',updatedAt:t},
             {id:'j2',name:'Shedwick',status:'Active',client:'Courtney Benson',clientPhone:'7185304980',address:'12 Shed Rd',updatedAt:t}];
  DB.contacts = [{id:'c1',type:'Contractor',name:'Ali Alycraft',company:'Alycraft LLC',phone:'2015551487',email:'ali@aly.com',skills:['Plumbing']},
                 {id:'c2',type:'Contractor',name:'Bob Volt',company:'Volt Electric',phone:'9735550000',email:'bob@volt.com',skills:['Electric']},
                 {id:'c3',type:'Client',name:'Shelden Washington',phone:'8626869866',email:'hrlm2philly@gmail.com'}];
  DB.contractors = [{id:'k1',jobId:'j1',contactId:'c1',name:'Ali Alycraft',company:'Alycraft LLC',value:5000,trade:'Plumbing'},{id:'k2',jobId:'j1',contactId:'c2',name:'Bob Volt',company:'Volt Electric',value:3000,trade:'Electric'}];
  bpSave(); }"""
VIS = "(function(id){ var e=document.getElementById(id); return !!(e && e.offsetParent); })"
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\niPhone')
            ctx = await b.new_context(viewport={'width':402,'height':874}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            await pg.evaluate(SEED); await pg.evaluate("bpPhoneBookOpen()"); await pg.wait_for_timeout(600)
            ok(await pg.evaluate(VIS + "('bp696-bar')"), 'the ≡ / search / ••• row is there')
            ok(not await pg.evaluate(VIS + "('bsp-pb-seg')") and not await pg.evaluate(VIS + "('bp-sb-q')"), 'the old Subs|Clients tabs and the "Search" box are gone')
            ok('Contractors & subs' in await pg.evaluate("document.getElementById('bp696-list').textContent"), '≡ shows "Contractors & subs"')
            ok(await pg.evaluate("!/search/i.test(document.getElementById('bp696-search').textContent)"), 'search is an icon, no word')
            await pg.screenshot(path='/tmp/claude-0/-home-claude/c39b4637-c61c-5ce3-97d7-41be4d0675a0/scratchpad/pb_phone.png')
            await pg.tap('#bp696-search'); await pg.wait_for_timeout(300)
            ok(await pg.evaluate(VIS + "('bp696-q')") and await pg.evaluate("document.querySelectorAll('#bp696-srow [data-fo]').length") == 5, 'search icon opens a box with 5 options')
            await pg.fill('#bp696-q', 'volt'); await pg.wait_for_timeout(300)
            vis = await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-sb-list .bp-ub'), function(c){ return c.style.display !== 'none'; }).length")
            ok(vis == 1, 'typing "volt" shows 1 sub (%s)' % vis)
            await pg.tap('#bp696-srow [data-fo="name"]'); await pg.wait_for_timeout(300)
            vis = await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-sb-list .bp-ub'), function(c){ return c.style.display !== 'none'; }).length")
            ok(vis == 1 and await pg.evaluate("document.getElementById('bp696-q').value") == 'volt', 'option Name keeps the text and still finds Bob Volt')
            await pg.tap('#bp696-srow [data-fo="email"]'); await pg.fill('#bp696-q', 'aly.com'); await pg.wait_for_timeout(300)
            names = await pg.evaluate("[].filter.call(document.querySelectorAll('#bp-sb-list .bp-ub'), function(c){ return c.style.display !== 'none'; }).map(function(c){ return c.textContent.slice(0,12); })")
            ok(len(names) == 1 and 'Ali' in names[0], 'option Email: "aly.com" finds Ali only (%s)' % names)
            await pg.tap('#bp696-qx'); await pg.wait_for_timeout(300)
            ok(not await pg.evaluate(VIS + "('bp696-q')") and await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length") == 2, 'X closes search, both subs back')
            await pg.tap('#bp696-skills'); await pg.wait_for_timeout(300)
            items = await pg.evaluate("[].map.call(document.querySelectorAll('#bp696-menu button'), function(b){ return b.textContent; })")
            ok(items == ['All skills', 'Electric', 'Plumbing'], '••• lists the skills (%s)' % items)
            ok(await pg.evaluate("(function(){ var m=document.getElementById('bp696-menu').getBoundingClientRect(); var e=document.elementFromPoint(m.left+40, m.top+30); return !!e.closest('#bp696-menu'); })()"), 'the menu is on top of everything')
            await pg.click('#bp696-menu button:nth-child(3)'); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length") == 1 and await pg.evaluate(VIS + "('bp696-tag')"), 'picking Plumbing shows 1 sub and a Plumbing tag')
            await pg.click('#bp696-tag button'); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length") == 2, 'tapping the tag clears it')
            await pg.tap('#bp696-list'); await pg.wait_for_timeout(300)
            items = await pg.evaluate("[].map.call(document.querySelectorAll('#bp696-menu button'), function(b){ return b.textContent; })")
            ok(len(items) == 2 and items[0] == 'Contractors & subs' and items[1].startswith('Clients'), '≡ menu: Contractors & subs · Clients (%s)' % items)
            await pg.click('#bp696-menu button:nth-child(2)'); await pg.wait_for_timeout(500)
            ok('Clients' in await pg.evaluate("document.getElementById('bp696-list').textContent") and not await pg.evaluate(VIS + "('bp696-skills')"), 'Clients list open; no skills ••• there')
            await pg.tap('#bp696-search'); await pg.fill('#bp696-q', '862'); await pg.tap('#bp696-srow [data-fo="cell"]'); await pg.wait_for_timeout(300)
            cl = await pg.evaluate("[].filter.call(document.getElementById('bsp-cl-list').children, function(c){ return c.style.display !== 'none'; }).map(function(c){ return c.textContent.slice(0,16); })")
            ok(len(cl) == 1 and 'Shelden' in cl[0], 'client search by Cell "862" finds Shelden (%s)' % cl)
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            print('\nMac')
            ctx = await b.new_context(viewport={'width':1440,'height':900})
            pg = await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
            await pg.evaluate(SEED); await pg.evaluate("showView('contacts')"); await pg.wait_for_timeout(600)
            ok(await pg.evaluate(VIS + "('bp696-dbar')") and not await pg.evaluate(VIS + "('contact-type-filter')"), '"All Types" box replaced by ≡ / search / •••')
            await pg.screenshot(path='/tmp/claude-0/-home-claude/c39b4637-c61c-5ce3-97d7-41be4d0675a0/scratchpad/pb_mac.png')
            await pg.click('#bp696-dlist'); await pg.wait_for_timeout(300)
            items = await pg.evaluate("[].map.call(document.querySelectorAll('#bp696-menu button'), function(b){ return b.textContent; })")
            ok('Contractors & subs' in items and 'Clients' in items, '≡ menu lists the contact types (%s)' % items)
            await pg.click('#bp696-menu button:has-text("Contractors & subs")'); await pg.wait_for_timeout(400)
            rows = await pg.evaluate("[].filter.call(document.querySelectorAll('#contacts-wrap tbody tr'), function(r){ return r.style.display !== 'none'; }).length")
            ok(rows == 2 and await pg.evaluate("document.getElementById('contact-type-filter').value") == 'Contractor', 'picked Contractors & subs: 2 rows')
            await pg.click('#bp696-dsearch'); await pg.fill('#bp696-q', 'volt'); await pg.wait_for_timeout(300)
            rows = await pg.evaluate("[].filter.call(document.querySelectorAll('#contacts-wrap tbody tr'), function(r){ return r.style.display !== 'none'; }).length")
            ok(rows == 1, 'search "volt": 1 row')
            await pg.click('#bp696-qx'); await pg.click('#bp696-dskills'); await pg.wait_for_timeout(300)
            await pg.click('#bp696-menu button:has-text("Plumbing")'); await pg.wait_for_timeout(300)
            rows = await pg.evaluate("[].filter.call(document.querySelectorAll('#contacts-wrap tbody tr'), function(r){ return r.style.display !== 'none'; }).map(function(r){ return r.children[0].textContent; })")
            ok(len(rows) == 1 and 'Ali' in rows[0], 'skill Plumbing: Ali only (%s)' % rows)
            ok(not errs, 'no page errors %s' % errs[:2])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
