"""v6.9.16 — (1) night weather icon (moon after sunset, sun by day) on iPhone and Command Center;
(2) undo bar after a delete is gone in about a second; (3) inside the app, no second web lock screen
after Face ID (browser keeps it); (4) no visible jumping on launch, between screens or opening a space
(iPhone); (5) adding checklist items goes straight on to the next one (iPhone sheet + Command Center window).
Run from repo root: python3 test_v6916_night_jumpy_addnext.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json, datetime
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8916
BLOCK = ('nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
OBS = """window.__ls=[];try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){ if(e.value<0.002) return;
 var bc=document.getElementById('bp-boot'), st=document.querySelector('.screen.bp-settling');
 window.__ls.push({hidden:!!(bc&&bc.style.opacity!=='0')||!!st, v:e.value, src:(e.sources||[]).map(function(s){ return s.node && (s.node.id || s.node.className || s.node.nodeName); }).slice(0,2).join(',')});});}).observe({type:'layout-shift',buffered:true});}catch(e){}"""
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'N. Peach St', client:'Anna Lee', address:'12 Peach St', status:'Active', contractValue:48000, startDate:'2026-10-01', updatedAt:t },
            { id:'j2', name:'Elm Ave', client:'B', address:'2 Elm', status:'Active', updatedAt:t }];
 DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', updatedAt:t }];
 DB.punchlist = []; for (var i = 1; i <= 20; i++) DB.punchlist.push({ id:'p'+i, jobId:'j1', roomId:'r1', text:'Item number '+i, done:i>12, updatedAt:t });
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
def wx_body(night):
    # sunrise/sunset around "now" in UTC so the test works any time of day
    n = datetime.datetime.utcnow()
    if night: sr, ss = n + datetime.timedelta(hours=3), n + datetime.timedelta(hours=13)
    else:     sr, ss = n - datetime.timedelta(hours=3), n + datetime.timedelta(hours=5)
    f = lambda d: d.strftime('%Y-%m-%dT%H:%M')
    return json.dumps({'utc_offset_seconds': 0, 'current_weather': {'temperature': 41, 'weathercode': 0, 'is_day': 0 if night else 1},
                       'current': {'temperature_2m': 41, 'weather_code': 0, 'is_day': 0 if night else 1},
                       'daily': {'sunrise': [f(sr)], 'sunset': [f(ss)]}})
async def page(b, url, night=True, shell=True, obs=False, **kw):
    ctx = await b.new_context(**kw)
    if shell: await ctx.add_init_script(SHELL)
    if obs: await ctx.add_init_script(OBS)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    body = wx_body(night)
    async def wx(route): await route.fulfill(status=200, content_type='application/json', body=body)
    await pg.route('**/api.open-meteo.com/**', wx)
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.fallback())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    return ctx, pg, errs
ICON = "(function(id){ var e = document.getElementById(id); var i = e && e.querySelector('.bp-ic'); return i ? i.getAttribute('aria-label') : (e ? e.textContent : ''); })"
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
      async with async_playwright() as p:
        b = await p.chromium.launch()
        PH = dict(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
        CC = dict(viewport={'width': 1180, 'height': 820}, user_agent=IPAD, has_touch=True)

        print('\n1. Weather by time of day')
        for night in (True, False):
            ctx, pg, errs = await page(b, 'index.html', night=night, geolocation={'latitude': 40.9268, 'longitude': -73.9957}, permissions=['geolocation'], **PH)
            await pg.evaluate("bpGeoRefresh && bpGeoRefresh()"); await pg.wait_for_timeout(2500)
            ic = await pg.evaluate(ICON + "('info-weather-icon')"); tx = await pg.inner_text('#info-weather-text')
            ok(ic == ('moon' if night else 'sun'), 'iPhone %s: %s icon, line icon (%s)' % ('3am' if night else 'noon', 'moon' if night else 'sun', ic))
            ok(('Clear Night' in tx) == night, 'iPhone: text reads "%s"' % tx)
            await ctx.close()
            ctx, pg, errs = await page(b, 'desktop.html', night=night, **CC)
            await pg.wait_for_timeout(2500)
            ic = await pg.evaluate(ICON + "('tb-wico')")
            ok(ic == ('moon' if night else 'sun'), 'Command Center %s: %s (%s)' % ('night' if night else 'day', 'moon' if night else 'sun', ic))
            await ctx.close()

        print('\n2. Lock screens')
        ctx, pg, errs = await page(b, 'index.html', **PH)
        ok(not await pg.evaluate("!!document.getElementById('bp-lock')"), 'iPhone app: no second (web) lock after Face ID')
        ok(await pg.evaluate("typeof bpHasPasscode === 'function' && typeof bpFaceIDSetup === 'function'"), 'iPhone app: passcode tools still loaded for Settings')
        await ctx.close()
        ctx, pg, errs = await page(b, 'index.html', shell=False, **PH)
        ok(await pg.evaluate("(function(){ var l = document.getElementById('bp-lock'); return !!l && getComputedStyle(l).display !== 'none'; })()"), 'Safari / Home Screen: web lock still shows (its only lock)')
        await ctx.close()
        ctx, pg, errs = await page(b, 'desktop.html', **CC)
        ok(not await pg.evaluate("!!document.getElementById('bp-lock')"), 'iPad Command Center app: no second lock')
        await ctx.close()

        print('\n3. No jumping (iPhone, job On Site)')
        ctx, pg, errs = await page(b, 'index.html', obs=True, **PH)
        await pg.evaluate(SEED); await pg.evaluate("bpSetActiveJob('j1')"); await pg.wait_for_timeout(800)
        await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(6000)
        vis = lambda L: round(sum(x['v'] for x in L if not x['hidden']), 3)
        L = await pg.evaluate("window.__ls")
        ok(vis(L) < 0.01, 'launch: nothing you can see moves (%s visible; %s hidden behind the cover)' % (vis(L), round(sum(x['v'] for x in L if x['hidden']), 3)))
        ok(not await pg.evaluate("!!document.getElementById('bp-boot')"), 'launch cover is gone once settled')
        await pg.evaluate("window.__ls = []")
        for sc in ('s-jobs', 's-punch', 's-home'): await pg.evaluate("showScreen('%s')" % sc); await pg.wait_for_timeout(1200)
        L = await pg.evaluate("window.__ls"); ok(vis(L) < 0.01, 'switching screens: no visible shift %s' % vis(L))
        await pg.evaluate("window.__ls = []; openRoomDetail('r1')"); await pg.wait_for_timeout(1400)
        L = await pg.evaluate("window.__ls"); ok(vis(L) < 0.01, 'opening a space: no visible shift %s %s' % (vis(L), [x['src'] for x in L if not x['hidden']]))
        ok(await pg.evaluate("!document.querySelector('.screen.bp-settling')"), 'screens are not left hidden')

        print('\n4. Undo bar after a delete')
        await pg.evaluate("bpDeletedToast('punchlist', DB.punchlist[0])"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!!document.getElementById('bp-undo-toast')"), 'undo bar shows')
        await pg.wait_for_timeout(1000)
        ok(not await pg.evaluate("!!document.getElementById('bp-undo-toast')"), 'gone in about a second (was 8 s)')

        print('\n5. Add checklist items, straight on to the next (iPhone)')
        n0 = await pg.evaluate("DB.punchlist.length")
        await pg.evaluate("openAddNote('j1','r1')"); await pg.wait_for_timeout(400)
        await pg.fill('#an-text', 'Set vanity'); await pg.click('#sheet-add-note .btn-primary'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.getElementById('sheet-add-note').classList.contains('open')"), 'sheet stays open after + Add Item')
        ok(await pg.evaluate("document.activeElement && document.activeElement.id === 'an-text' && document.getElementById('an-text').value === ''"), 'description cleared, cursor in it for the next item')
        await pg.fill('#an-text', 'Caulk tub'); await pg.press('#an-text', 'Enter'); await pg.wait_for_timeout(300)
        await pg.fill('#an-text', 'Hang mirror'); await pg.press('#an-text', 'Enter'); await pg.wait_for_timeout(300)
        new = await pg.evaluate("DB.punchlist.slice(-3).map(function(n){ return [n.text, n.roomId, n.jobId]; })")
        ok(await pg.evaluate("DB.punchlist.length") == n0 + 3 and [x[0] for x in new] == ['Set vanity', 'Caulk tub', 'Hang mirror'], 'three in a row, Return key works too ' + str([x[0] for x in new]))
        ok(all(x[1] == 'r1' and x[2] == 'j1' for x in new), 'all three land in this space and job')
        ok('3 added' in await pg.inner_text('#sheet-add-note'), 'sheet counts them ("3 added")')
        await pg.click('#an-text'); await pg.press('#an-text', 'Enter'); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.punchlist.length") == n0 + 3, 'empty Return adds nothing')
        await pg.evaluate("closeSheet('sheet-add-note')"); await pg.wait_for_timeout(300)
        await pg.evaluate("openAddNote('j1','r1')"); await pg.wait_for_timeout(300)
        ok('added' not in await pg.inner_text('#sheet-add-note'), 'count starts over next time')
        ok(not errs, 'iPhone: no script errors ' + str(errs[:2]))
        await ctx.close()

        print('\n6. Add checklist items, straight on to the next (Command Center)')
        ctx, pg, errs = await page(b, 'desktop.html', **CC)
        await pg.evaluate(SEED); await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
        n0 = await pg.evaluate("DB.punchlist.length")
        await pg.evaluate("closeRoomDetailAnd(function(){ openNewCheckItem('j1','r1'); })"); await pg.wait_for_timeout(400)
        await pg.fill('#nc2-text', 'Patch drywall'); await pg.click('#modal-new-check .btn:not(.btn-ghost)'); await pg.wait_for_timeout(300)
        await pg.fill('#nc2-text', 'Prime walls'); await pg.press('#nc2-text', 'Enter'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.punchlist.length") == n0 + 2, 'two in a row (button, then Return)')
        ok(await pg.evaluate("document.activeElement && document.activeElement.id === 'nc2-text' && !document.getElementById('nc2-text').value"), 'window stays open, cleared, cursor ready')
        ok('2 added' in await pg.inner_text('#modal-new-check'), 'window counts them')
        await pg.evaluate("closeModal('modal-new-check')"); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("!!document.getElementById('modal-room-detail')"), 'closing it goes back to the space')
        await pg.locator('#bp-desk-checklist > div:visible').first.locator('button').first.click(); await pg.wait_for_timeout(400)
        ok((await pg.evaluate("document.querySelector('#modal-new-check .btn:not(.btn-ghost)').textContent")).strip() == 'Update Item' and 'added' not in await pg.inner_text('#modal-new-check'), 'Edit is still one item: Update, no count')
        nn = await pg.evaluate("DB.punchlist.length")
        await pg.fill('#nc2-text', 'Renamed'); await pg.click('#modal-new-check .btn:not(.btn-ghost)'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.punchlist.length") == nn and not await pg.evaluate("document.getElementById('modal-new-check').classList.contains('open') && getComputedStyle(document.getElementById('modal-new-check')).display !== 'none'"), 'Update saves and closes, no extra item')
        ok(not errs, 'Command Center: no script errors ' + str(errs[:2]))
        await ctx.close()
        await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
