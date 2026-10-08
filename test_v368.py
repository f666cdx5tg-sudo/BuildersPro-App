"""BuildersPro v3.68 (offline queue + "waiting to sync"; builds on v3.67).
Fake GitHub gist server inside Playwright, so no real network/token. Run from the repo root:
python3 test_v368.py  (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)

CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'}
class Fake:
    def __init__(s): s.files = {}; s.fail = False; s.delay = 0; s.calls = 0; s.attempts = 0
    async def handle(s, route, req):
        if req.method == 'OPTIONS': return await route.fulfill(status=204, headers=CORS)
        s.attempts += 1
        if s.fail: return await route.abort()
        if s.delay: await asyncio.sleep(s.delay)
        s.calls += 1
        def body(): return json.loads(req.post_data or '{}')
        if req.method == 'POST' and req.url.rstrip('/').endswith('/gists'):
            for k, v in body().get('files', {}).items(): s.files[k] = {'filename': k, 'content': v['content'], 'truncated': False}
            return await route.fulfill(status=201, headers=CORS, content_type='application/json', body=json.dumps({'id': 'g1', 'owner': {'login': 't'}, 'files': s.files}))
        if req.method == 'PATCH':
            for k, v in body().get('files', {}).items():
                if v is None: s.files.pop(k, None)
                else: s.files[k] = {'filename': k, 'content': v['content'], 'truncated': False}
            return await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'id': 'g1', 'files': s.files}))
        return await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'id': 'g1', 'owner': {'login': 't'}, 'files': s.files}))

SEED = """(()=>{DB.jobs=[{id:'j1',name:'Test Job',status:'Active'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen'}];save();})()"""
ADD3 = """(()=>{DB.expenses.push({id:'e1',jobId:'j1',desc:'Copper fittings',amount:42,date:'2026-10-08'});
DB.punchlist.push({id:'p1',jobId:'j1',roomId:'r1',text:'Seal under sink',done:false});
DB.photos.push({id:'ph1',jobId:'j1',roomId:'r1',data:'data:image/png;base64,'+'A'.repeat(900),date:new Date().toISOString()});save();})()"""

async def wait_for(pg, js, timeout=40000):
    try: await pg.wait_for_function(js, timeout=timeout); return True
    except Exception: return False

async def main_test(w, h):
    fake = Fake()
    async def net(on, ctx):
        fake.fail = not on; await ctx.set_offline(not on)
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await ctx.route('https://api.github.com/**', fake.handle)
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        ok(await pg.evaluate("APP_VERSION==='3.68'"), 'version is not 3.68')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        ok(await pg.evaluate("typeof bpPending==='function' && !!document.getElementById('bp-q-chip')"), 'queue module not loaded')
        # no sync set up -> chip never shows
        await pg.evaluate(SEED); await pg.wait_for_timeout(1200)
        ok(not await pg.evaluate("document.getElementById('bp-q-chip').classList.contains('on')"), 'chip should be hidden when sync is not set up')
        # set up sync -> first backup establishes the baseline
        await pg.evaluate("_syncToken='ghp_test'; save();")
        ok(await wait_for(pg, "(()=>{const d=bpPending();return !d.unknown&&d.total===0&&localStorage.getItem('bp_pend_base')})()", 60000), 'first backup never finished / baseline not stored')
        ok('Test Job' in json.dumps(fake.files.get('bp_data.json', {})), 'fake cloud did not receive the job')
        ok(not await pg.evaluate("document.getElementById('bp-q-chip').classList.contains('on')"), 'chip should hide when everything is synced')

        # ---- go offline, make 3 changes ----
        await net(False, ctx); await pg.wait_for_timeout(300); calls0 = fake.attempts
        await pg.evaluate(ADD3); await pg.wait_for_timeout(1500)
        d = await pg.evaluate("bpPending()")
        ok(d['total'] == 3 and not d['unknown'], f'expected 3 waiting, got {d["total"]}')
        kinds = sorted(i['col'] for i in d['items']); ok(kinds == ['expenses', 'photos', 'punchlist'], f'wrong waiting kinds {kinds}')
        chip = await pg.evaluate("(()=>{const c=document.getElementById('bp-q-chip');return {on:c.classList.contains('on'),t:c.textContent}})()")
        ok(chip['on'] and 'Offline' in chip['t'] and '3 waiting' in chip['t'], f'offline chip wrong: {chip}')
        await pg.wait_for_timeout(9500)   # past the old 8s auto-push: offline must not attempt it or flag failure
        ok(fake.attempts == calls0, f'app tried to reach the cloud while offline ({fake.attempts - calls0} requests)')
        ok(not await pg.evaluate("(typeof _lastSyncError!=='undefined')&&!!_lastSyncError"), 'offline should not record a sync failure')
        # sheet
        await pg.click('#bp-q-chip'); await pg.wait_for_timeout(300)
        sheet = await pg.evaluate("document.getElementById('bp-q-sheet').innerText")
        ok('3 waiting to sync' in sheet and 'Copper fittings' in sheet and 'Seal under sink' in sheet and 'Test Job' in sheet and 'No signal' in sheet, f'sheet content wrong: {sheet[:300]!r}')
        ok(await pg.evaluate("(()=>{const r=document.querySelector('#bp-q-sheet .qr span:nth-child(2)');return !!r&&getComputedStyle(r).whiteSpace==='nowrap'})()"), 'item names must not wrap')
        await pg.click('#bp-q-close'); await pg.wait_for_timeout(200)

        # ---- app restart with signal but the cloud refusing: list must survive ----
        await ctx.set_offline(False); fake.fail = True   # signal, but cloud refuses
        await pg.reload(); await pg.wait_for_timeout(3000)
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        d = await pg.evaluate("bpPending()")
        ok(d['total'] == 3, f'waiting list did not survive a restart: {d["total"]}')

        # ---- signal returns -> automatic upload ----
        await net(False, ctx); await pg.wait_for_timeout(200)
        await net(True, ctx)   # fires the 'online' event
        ok(await wait_for(pg, "bpPending().total===0", 60000), 'did not auto-sync after signal returned')
        cloud = json.dumps(fake.files)
        ok('Copper fittings' in cloud and 'Seal under sink' in cloud, 'cloud is missing the offline changes')
        await pg.wait_for_timeout(500)
        ok(not await pg.evaluate("document.getElementById('bp-q-chip').classList.contains('on')"), 'chip should hide after the queue drains')

        # ---- a change made DURING a backup must stay on the list ----
        fake.delay = 1.5
        await pg.evaluate("window.__pp = doPush()"); await pg.wait_for_timeout(500)
        await pg.evaluate("DB.expenses.push({id:'e2',jobId:'j1',desc:'Mid-push item',amount:5});save();")
        await pg.evaluate("window.__pp"); fake.delay = 0
        await pg.wait_for_timeout(300)
        d = await pg.evaluate("bpPending()")
        ok(any(i['label'].startswith('Mid-push item') for i in d['items']) or 'Mid-push item' in json.dumps(fake.files), 'mid-push change was lost track of')
        ok(await wait_for(pg, "bpPending().total===0", 60000), 'queue did not drain after mid-push change')
        ok('Mid-push item' in json.dumps(fake.files), 'mid-push change never reached the cloud')

        # ---- deletion is tracked ----
        await net(False, ctx)
        await pg.evaluate("DB.expenses=DB.expenses.filter(e=>e.id!=='e1');save();"); await pg.wait_for_timeout(1200)
        d = await pg.evaluate("bpPending()")
        ok(d['total'] == 1 and d['items'][0]['action'] == 'deleted', f'deletion not tracked: {d}')
        await net(True, ctx)
        ok(await wait_for(pg, "bpPending().total===0", 60000), 'deletion did not sync')
        ok(len(errs) == 0, f'console errors: {errs[:3]}')
        await b.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8799', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await main_test(390, 844)
        await main_test(834, 1194)
    finally: srv.terminate()
    print(f'{checks - len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
