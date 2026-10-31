"""v6.7.0 — iCloud Drive sync with no sign-in (simulated app + iCloud folder shared by two devices).
iPhone adds a punch item with a photo → Mac gets it (photo too). Mac ticks it done → iPhone sees done.
A delete on one device stays deleted on the other. No Apple sign-in box anywhere.
Run from repo root: python3 test_v670_drive_sync.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8970
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
async def dev(b, file, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    await ctx.expose_function('__drive', drive)
    await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2600)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
    return ctx, pg, errs
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            c1, phone, e1 = await dev(b, 'index.html', 402, 874)
            c2, mac, e2 = await dev(b, 'desktop.html', 1440, 900)
            await phone.evaluate("(png) => { var t=new Date().toISOString(); DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active',updatedAt:t}]; DB.punchlist=[{id:'k1',jobId:'j1',text:'Set flange',done:false,updatedAt:t}]; DB.photos=[{id:'ph1',jobId:'j1',src:png,date:t,updatedAt:t}]; bpSave(); }", PNG)
            await mac.evaluate("DB.jobs=[]; DB.punchlist=[]; DB.photos=[]; bpSave();")
            print('\niPhone → iCloud → Mac')
            r = await phone.evaluate("bpDriveSync()")
            ok(r is not None and 'state-' in ' '.join(FILES) and any(n.startswith('p/') for n in FILES), 'phone wrote its copy and the photo to iCloud Drive %s' % r)
            await mac.wait_for_timeout(300)
            r = await mac.evaluate("bpDriveSync()")
            got = await mac.evaluate("({k: DB.punchlist.map(function(x){return x.text}), ph: (DB.photos[0]||{}).src && DB.photos[0].src.slice(0,22)})")
            ok(got['k'] == ['Set flange'] and got['ph'] == 'data:image/png;base64,', 'Mac has the punch item and the photo %s' % got)
            print('\nMac → iCloud → iPhone')
            await mac.wait_for_timeout(50)
            await mac.evaluate("var k=DB.punchlist[0]; k.done=true; k.updatedAt=new Date().toISOString(); bpSave();")
            await mac.evaluate("bpDriveSync()"); await phone.wait_for_timeout(50)
            await phone.evaluate("bpDriveSync()")
            ok(await phone.evaluate("DB.punchlist[0].done") is True, 'phone sees it ticked done')
            print('\nDeletes stay deleted')
            await phone.evaluate("bpRemoveFrom('punchlist', function(x){ return x.id !== 'k1'; }); bpSave();")
            await phone.evaluate("bpDriveSync()"); await mac.evaluate("bpDriveSync()")
            ok(await mac.evaluate("DB.punchlist.length") == 0, 'deleted on the phone → gone on the Mac')
            await mac.evaluate("bpDriveSync()"); await phone.evaluate("bpDriveSync()")
            ok(await phone.evaluate("DB.punchlist.length") == 0, 'and it does not come back to the phone')
            print('\nNo sign-in')
            await phone.wait_for_timeout(9500); await phone.evaluate("bpSaveChipPaint()")
            ok(await phone.evaluate("__bpCk().drive === true && !__bpCk().err"), 'sync status: iCloud Drive, no error')
            txt = await phone.evaluate("(document.getElementById('bp-save-chip')||{}).textContent || ''")
            ok('synced' in txt.lower(), 'save bar says synced (%s)' % txt)
            ok(not e1 and not e2, 'no page errors %s %s' % (e1[:2], e2[:2]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
