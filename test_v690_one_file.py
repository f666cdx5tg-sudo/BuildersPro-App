"""v6.9.0 — one shared file. Three devices (iPhone, Mac, iPad) share ONE iCloud Drive file.
Covers: first device writes it (+ backup), others load it; edits on two devices at once keep both;
a save overwritten by another device is put back; delete wins and never comes back; an iPad with an
old copy (deleted job, merged duplicate) joins without bringing them back; 10 rounds of syncing on
all devices never duplicates a job or changes a money total; closing and reopening loads the file.
Run from repo root: python3 test_v690_one_file.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8990
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
FILES = {}
SHELL = """
window.BPShell = { version: 't', caps: { ai: true, drive: true } };
window.webkit = { messageHandlers: { bp: { postMessage: function(m){
  if (m.kind && m.kind.indexOf('drive') === 0) window.__drive(JSON.stringify(m)).then(function(r){ window.bpDriveDone(m.id, JSON.parse(r)); });
} } } };
"""
async def drive(raw):
    m = json.loads(raw); k = m['kind']
    if k == 'drivePut': FILES[m['name']] = (m['text'], time.time() * 1000); return json.dumps({'ok': True})
    if k == 'driveGet':
        f = FILES.get(m['name']); return json.dumps({'ok': True, 'text': f[0]} if f else {'ok': False})
    return json.dumps({'ok': True, 'states': [{'name': n, 'at': v[1]} for n, v in FILES.items() if n.startswith('state-')], 'photos': [n[2:-4] for n in FILES if n.startswith('p/')]})
PNG = 'data:image/png;base64,' + 'iVBORw0KGgo' * 400
async def dev(b, file, w, h, ctx=None):
    if ctx is None:
        ctx = await b.new_context(viewport={'width': w, 'height': h})
        await ctx.expose_function('__drive', drive)
        await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2600)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
    return ctx, pg, errs
JOBS = "DB.jobs.map(function(j){return j.name}).sort().join(',')"
MONEY = "Math.round((DB.expenses||[]).reduce(function(s,e){return s+(+e.amount||0)},0)*100)/100 + '|' + Math.round((DB.payments||[]).reduce(function(s,e){return s+(+e.amount||0)},0)*100)/100"
def shared(): return json.loads(FILES['state-shared.json'][0])
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            c1, phone, e1 = await dev(b, 'index.html', 402, 874)
            c2, mac, e2 = await dev(b, 'desktop.html', 1440, 900)
            ok(await phone.evaluate("APP_VERSION") >= '6.9.0', 'version 6.9.0 or later')
            SEED = """(png) => { var t='2026-10-31T12:00:00.000Z';
              DB.jobs=[{id:'jA',name:'N. Peach St',status:'Active',updatedAt:t},{id:'jB',name:'Shedwick',status:'Active',updatedAt:t}];
              DB.punchlist=[{id:'k1',jobId:'jA',text:'Set flange',done:false,updatedAt:t}];
              DB.expenses=[{id:'e1',jobId:'jA',amount:1200.50,date:'2026-10-01',vendor:'HD',updatedAt:t},{id:'e2',jobId:'jB',amount:300,date:'2026-10-02',vendor:'Lowes',updatedAt:t}];
              DB.payments=[]; DB.photos=[{id:'ph1',jobId:'jA',src:png,updatedAt:t}];
              DB.tombstones={'jobs:jDel':'2026-10-20T00:00:00.000Z'}; DB.jobMerges={jDup:'jA'}; DB.keepStamps={};
              bpSave(); }"""
            await phone.evaluate(SEED, PNG)
            await mac.evaluate(SEED, PNG)
            print('\nFirst device writes the one file; a backup of each device first')
            await phone.evaluate("bpDriveSync()")
            ok('state-shared.json' in FILES, 'the shared file is in iCloud Drive')
            ok(any(n.startswith('pre690-dev-') for n in FILES), "phone's own copy backed up (pre690-…json)")
            await mac.evaluate("bpDriveSync()")
            ok(any(n.startswith('pre690-mac-') for n in FILES), "Mac's own copy backed up")
            ok(await mac.evaluate(JOBS) == 'N. Peach St,Shedwick' and await mac.evaluate(MONEY) == '1500.5|0', 'Mac joined: 2 jobs, $1,500.50 — no doubles')
            print('\nEdits on two devices at the same time: both kept')
            await phone.evaluate("var k=DB.punchlist[0]; k.done=true; k.updatedAt=new Date().toISOString(); bpSave();")
            await mac.evaluate("DB.jobs.push({id:'jT',name:'Sync Test Job',status:'Active',updatedAt:new Date().toISOString()}); bpSave();")
            await phone.evaluate("bpDriveSync()"); await mac.evaluate("bpDriveSync()"); await phone.evaluate("bpDriveSync()")
            for pg, nm in ((phone, 'phone'), (mac, 'Mac')):
                ok(await pg.evaluate(JOBS) == 'N. Peach St,Shedwick,Sync Test Job' and await pg.evaluate("DB.punchlist[0].done") is True, nm + ': has the new job AND the punch tick')
            print('\nDelete wins and stays deleted')
            await mac.evaluate("bpRemoveFrom('jobs', function(j){ return j.id !== 'jT'; }); bpSave();")
            await mac.evaluate("bpDriveSync()"); await phone.evaluate("bpDriveSync()")
            ok('Sync Test Job' not in await phone.evaluate(JOBS), 'deleted on the Mac → gone on the phone')
            ok('jT' not in json.dumps([j['id'] for j in shared()['db']['jobs']]), 'and gone from the shared file')
            await phone.evaluate("var k=DB.punchlist[0]; k.text='Set flange (edited)'; k.updatedAt=new Date().toISOString(); bpSave();")
            await phone.evaluate("bpDriveSync()"); await mac.evaluate("bpDriveSync()")
            ok('Sync Test Job' not in await mac.evaluate(JOBS) and 'Sync Test Job' not in await phone.evaluate(JOBS), 'more syncing never brings it back')
            print('\nA save overwritten by another device (iCloud delay) is put back')
            await mac.evaluate("bpDriveSync()"); await phone.evaluate("bpDriveSync()")
            stale = FILES['state-shared.json']
            await phone.evaluate("DB.expenses.push({id:'e3',jobId:'jB',amount:45,date:'2026-10-31',vendor:'Ace',updatedAt:new Date().toISOString()}); bpSave();")
            await phone.evaluate("bpDriveSync()")
            FILES['state-shared.json'] = stale            # the Mac never got the phone's save
            await mac.evaluate("DB.jobs[0].notes='gate code 1234'; DB.jobs[0].updatedAt=new Date().toISOString(); bpSave();")
            await mac.evaluate("bpDriveSync()")              # Mac writes on top of the old file: phone's expense is missing
            await phone.evaluate("bpDriveSync()"); await mac.evaluate("bpDriveSync()")
            for pg, nm in ((phone, 'phone'), (mac, 'Mac')):
                ok(await pg.evaluate(MONEY) == '1545.5|0' and await pg.evaluate("DB.jobs.filter(function(j){return j.notes==='gate code 1234'}).length") == 1, nm + ": the phone's $45 expense came back AND the Mac's note is kept (%s)" % await pg.evaluate(MONEY))
            print('\nAn iPad with an OLD copy joins')
            c3, ipad, e3 = await dev(b, 'index.html', 820, 1180)
            await ipad.evaluate("""(png) => { var t='2026-10-25T00:00:00.000Z';
              DB.jobs=[{id:'jA',name:'N. Peach St',status:'Active',updatedAt:'2026-10-01T00:00:00.000Z'},{id:'jB',name:'Shedwick',status:'Active',updatedAt:'2026-10-01T00:00:00.000Z'},
                       {id:'jDel',name:'Test Kitchen Remodel',status:'Active',updatedAt:t},{id:'jDup',name:'N. Peach St',status:'Active',updatedAt:t},{id:'jNew',name:'iPad-only job',status:'Active',updatedAt:t}];
              DB.punchlist=[{id:'kD',jobId:'jDel',text:'old',updatedAt:t}]; DB.expenses=[{id:'e1',jobId:'jA',amount:1200.50,date:'2026-10-01',vendor:'HD',updatedAt:'2026-10-01T00:00:00.000Z'},{id:'eD',jobId:'jDup',amount:999,updatedAt:t}];
              DB.payments=[]; DB.photos=[]; bpSave(); }""", PNG)
            # a device that has never synced the one file: forget its one-file state
            await ipad.evaluate("() => new Promise(function(r){ idbDel('bp_one_base'); idbDel('bp_one_prev'); setTimeout(r, 300); })")
            await ipad.evaluate("bpDriveSync()")
            j = await ipad.evaluate(JOBS)
            ok(j == 'N. Peach St,Shedwick,iPad-only job', "deleted job and merged duplicate did NOT come back; the iPad's own new job is kept (%s)" % j)
            ok(await ipad.evaluate(MONEY) == '1545.5|0', 'money not doubled ($1,545.50)')
            ok(await ipad.evaluate("(DB.photos[0]||{}).src && DB.photos[0].src.slice(0,5)") == 'data:', 'iPad got the photo')
            print('\n10 rounds on all three devices')
            for i in range(10):
                for pg in (phone, mac, ipad): await pg.evaluate("bpDriveSync()")
            res = set()
            for pg in (phone, mac, ipad): res.add(await pg.evaluate(JOBS) + ' / ' + await pg.evaluate(MONEY) + ' / ' + str(await pg.evaluate("DB.jobs.length")))
            ok(len(res) == 1 and list(res)[0] == 'N. Peach St,Shedwick,iPad-only job / 1545.5|0 / 3', 'all three identical, no duplicates, money unchanged %s' % res)
            print('\nClose and reopen (5 times)')
            for i in range(5):
                await phone.close()
                c1, phone, e1b = await dev(b, 'index.html', 402, 874, c1)
                await phone.evaluate("bpDriveSync()")
                ok(await phone.evaluate(JOBS) == 'N. Peach St,Shedwick,iPad-only job' and await phone.evaluate(MONEY) == '1545.5|0' and not e1b, 'reopen %d: same 3 jobs, same money, no errors' % (i + 1))
            print('\nA brand-new device (nothing on it) gets everything')
            c4, fresh, e4 = await dev(b, 'desktop.html', 1440, 900)
            await fresh.evaluate("bpDriveSync()")
            ok(await fresh.evaluate(JOBS) == 'N. Peach St,Shedwick,iPad-only job' and await fresh.evaluate(MONEY) == '1545.5|0', 'new device shows the same 3 jobs and money')
            print('\nReopening straight onto Finance shows the real numbers')
            await phone.evaluate("showScreen('s-finance')"); await phone.wait_for_timeout(300)
            await phone.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:function(){return true}}); document.dispatchEvent(new Event('visibilitychange'));"); await phone.wait_for_timeout(600)
            await phone.close(); c1, phone, e1c = await dev(b, 'index.html', 402, 874, c1); await phone.wait_for_timeout(4000)
            txt = await phone.evaluate("document.getElementById('s-finance').innerText")
            ok(await phone.evaluate("document.querySelector('.screen.active').id") == 's-finance' and '1,545.50' in txt, 'Finance reopened with $1,545.50 in costs, not $0')
            print('\nA phone that opens EMPTY (data not loaded yet) can never wipe the shared file')
            await phone.evaluate("DB.jobs=[]; DB.expenses=[]; DB.punchlist=[]; DB.photos=[]; localStorage.setItem('bp_one_dirty', String(Date.now()));")
            r = await phone.evaluate("bpDriveSync()")
            ok(len(shared()['db']['jobs']) == 3, 'shared file still has 3 jobs %s' % r)
            ok(await phone.evaluate(JOBS) == 'N. Peach St,Shedwick,iPad-only job', 'and the phone took the shared data instead')
            await phone.evaluate("DB.jobs = DB.jobs.slice(0, 1); bpSave();")
            await phone.evaluate("bpDriveSync()")
            ok(len(shared()['db']['jobs']) == 3, 'a round that would drop 2 of 3 jobs at once is refused')
            print('\nIf the shared file was emptied, it is restored from the backup taken at the switch')
            old = shared()['db']; FILES['state-mac-old.json'] = (json.dumps({'db': old}), time.time() * 1000)   # the old per-device copies are still in iCloud Drive
            sf = shared(); sf['db']['jobs'] = []; sf['db']['expenses'] = []; sf['rev'] = 'wiped-1'; FILES['state-shared.json'] = (json.dumps(sf), time.time() * 1000)
            await mac.evaluate("bpDriveSync()")
            ok(len(shared()['db']['jobs']) >= 2 and 'N. Peach St' in await mac.evaluate(JOBS), 'Mac brought the jobs back from its backup (%s)' % await mac.evaluate(JOBS))
            await phone.evaluate("bpDriveSync()")
            ok('N. Peach St' in await phone.evaluate(JOBS), 'and the phone gets them from the shared file')
            print('\nDeleting a job on purpose never sets off the "jobs missing" alarm')
            await mac.evaluate("bpRemoveFrom('jobs', function(j){ return j.id !== 'jNew'; }); DB.jobs = DB.jobs.filter(function(j){ return j.id !== 'jNew'; }); bpSave();")
            await mac.close(); c2, mac, e2b = await dev(b, 'desktop.html', 1440, 900, c2); await mac.wait_for_timeout(12000)
            ok(not await mac.evaluate("!!(document.getElementById('bp-safety-banner') && /missing/.test(document.getElementById('bp-safety-banner').textContent))"), 'reopened 12 s later: no "1 job is missing" banner')
            ok(not e1 and not e2 and not e3 and not e4, 'no page errors %s' % (e1 + e2 + e3 + e4)[:2])
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
