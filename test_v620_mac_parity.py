"""v6.2.0 — the Command Center has the field app's job features, from the same code, through the Mac's
own screens. Each feature is used on the Mac and the result checked against the field app's rules.
Run from repo root: python3 test_v620_mac_parity.py   Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8891
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SHOT = os.environ.get('SHOTS', '')

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            dialogs = []
            async def on_dialog(d):
                dialogs.append(d.message); await (d.accept() if 'OK = save anyway' not in d.message or len(dialogs) > 1 else d.dismiss())
            pg.on('dialog', on_dialog)
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
            await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
            v = await pg.evaluate("APP_VERSION"); ok(v == '6.2.0', 'Mac on v6.2.0 (%s)' % v)

            print('\nBSP intake check on a new Mac job (same as the field app)')
            await pg.evaluate("openModal('modal-new-job')")
            await pg.fill('#nj-name', 'Parity Test Job'); await pg.fill('#nj-client', 'Dana Client'); await pg.fill('#nj-address', '12 Main St')
            await pg.evaluate("saveNewJob()"); await pg.wait_for_timeout(300)
            ok(any('missing the client email and cell' in d for d in dialogs), 'missing email and cell are named before saving')
            ok(not any(j['name'] == 'Parity Test Job' for j in await pg.evaluate("DB.jobs")), 'Cancel goes back without saving')
            await pg.fill('#nj-client-email', 'dana@example.com'); await pg.fill('#nj-client-phone', '2015550123')
            await pg.evaluate("saveNewJob()"); await pg.wait_for_timeout(400)
            job = await pg.evaluate("DB.jobs.find(function(j){ return j.name === 'Parity Test Job'; })")
            ok(job is not None, 'job saved once complete')
            jid = job['id'] if job else ''
            c = await pg.evaluate("(id) => (DB.contacts||[]).find(function(c){ return c.type === 'Client' && c.jobId === id; })", jid)
            ok(c and c['name'] == 'Dana Client' and c['email'] == 'dana@example.com', 'client card added to the phone book')

            print('\nJob page on the Mac')
            await pg.evaluate("(id) => { showView('job-detail'); renderDesktopJobDetail(id); }", jid); await pg.wait_for_timeout(500)
            t = await pg.evaluate("(document.getElementById('bsp-ready')||{}).innerText || ''")
            ok('BSP' in t and 'Signed contract' in t, 'BSP checklist card shows (%s)' % t.replace('\n', ' | ')[:90])
            ok(await pg.is_visible('#jd-security-section'), 'Security section shows')
            ok(await pg.is_visible('[data-bp620="co"]'), 'Change order button (purple) shows')
            ok(await pg.is_visible('[data-bp620="notes"]'), 'Note button shows')
            if SHOT: await pg.screenshot(path=SHOT + '/mac_job.png')

            print('\nSecurity on the Mac')
            await pg.evaluate("(id) => bpSecAdd(id)", jid); await pg.wait_for_timeout(200)
            await pg.select_option('#bpsec-kind', 'wifi'); await pg.evaluate("bpSecKindChange()")
            await pg.fill('#bpsec-label', 'Basement router'); await pg.fill('#bpsec-user', 'PeachNet'); await pg.fill('#bpsec-secret', 'hunter22')
            await pg.evaluate("bpSecSave()"); await pg.wait_for_timeout(300)
            sec = await pg.evaluate("(id) => DB.jobs.find(function(j){ return j.id === id; }).security", jid)
            ok(sec and sec[0]['kind'] == 'wifi' and sec[0]['user'] == 'PeachNet' and sec[0]['secret'] == 'hunter22', 'Wi-Fi entry saved on the job')
            txt = await pg.inner_text('#jd-security-section')
            ok('Basement router' in txt and 'hunter22' not in txt, 'listed, password hidden until clicked')
            await pg.click('[data-sec-val]'); await pg.wait_for_timeout(100)
            ok('hunter22' in await pg.inner_text('#jd-security-section'), 'click shows the password')

            print('\nGates')
            dialogs.clear()
            await pg.evaluate("(id) => toggleJobStarted(id)", jid); await pg.wait_for_timeout(200)
            ok(any('no signed contract on file' in d for d in dialogs), 'starting with no signed contract asks first')
            await pg.evaluate("(id) => openNewChangeOrder(id)", jid); await pg.wait_for_timeout(300)
            has = await pg.evaluate("!!document.getElementById('co-title') && !!document.getElementById('co-status')")
            ok(has, 'Change order sheet opens from the job page')
            if has:
                await pg.fill('#co-title', 'Extra outlet'); await pg.evaluate("document.getElementById('co-status').value = 'Approved'")
                amt = await pg.evaluate("!!document.getElementById('co-amount')")
                if amt: await pg.fill('#co-amount', '350')
                await pg.evaluate("saveChangeOrder()"); await pg.wait_for_timeout(300)
                n = await pg.evaluate("(DB.changeOrders||[]).filter(function(c){ return c.title === 'Extra outlet' && c.status === 'Approved'; }).length")
                ok(n == 0, 'an Approved change order without the owner\'s signature is not saved')
                await pg.evaluate("closeModal('modal-change-order')")

            print('\nFast / good / cheap on a Mac estimate')
            await pg.evaluate("openNewEstimateDesktop()"); await pg.wait_for_timeout(300)
            ok(await pg.is_visible('#bsp-pick2'), 'pick-two pie on the estimate sheet')
            await pg.fill('#est-title', 'Bathroom'); await pg.evaluate("_estLineItems = [{desc:'Rough + finish', qty:1, price:10000}]; renderEstItemsRows();")
            await pg.evaluate("bspPickTap('fast'); bspPickTap('good');")
            msg = await pg.inner_text('#p2-msg'); ok('Fast + Good' in msg, 'client picks Fast + Good (%s)' % msg[:40])
            pr = await pg.input_value('#p2-price-fg'); ok(pr == '12000', 'BSP suggests $12,000 for Fast + Good on a $10,000 estimate (%s)' % pr)
            await pg.evaluate("saveEstimateModalDesktop()"); await pg.wait_for_timeout(300)
            e = await pg.evaluate("DB.estimates.find(function(x){ return x.title === 'Bathroom'; })")
            ok(e and e.get('pick') == ['fast', 'good'] and str(e['pickOptions']['fg']['price']) == '12000', 'pick saved on the estimate (same fields as the field app)')

            print('\nNotes with a photo on the Mac')
            await pg.evaluate("(id) => { showView('job-detail'); renderDesktopJobDetail(id); }", jid); await pg.wait_for_timeout(300)
            await pg.click('[data-bp620="notes"]'); await pg.wait_for_timeout(300)
            ok(await pg.is_visible('#bp-notes-ov'), 'note editor opens')
            ok(await pg.evaluate("!!document.getElementById('bpn-text')"), 'note has a text box')
            if await pg.evaluate("!!document.getElementById('bpn-text')"):
                await pg.fill('#bpn-text', 'Customer wants matte black fixtures')
                saved = await pg.evaluate("""(function(){ var b = [].slice.call(document.querySelectorAll('#bp-notes-ov button')).find(function(x){ return /save/i.test(x.textContent); }); if (b) { b.click(); return true; } return false; })()""")
                await pg.wait_for_timeout(400)
                n = await pg.evaluate("(id) => (DB.jobNotes||[]).filter(function(n){ return n.jobId === id && /matte black/.test(n.text||''); }).length", jid)
                ok(saved and n == 1, 'note saved on the job (same record as the field app)')
                await pg.evaluate("(id) => renderDesktopJobDetail(id)", jid); await pg.wait_for_timeout(300)
                ok('matte black' in (await pg.evaluate("(document.getElementById('jd-notes')||{}).innerText||''")), 'note listed on the Mac job page')
            if SHOT: await pg.screenshot(path=SHOT + '/mac_job_after.png', full_page=False)

            print('\nSame names as the field app')
            side = await pg.evaluate("[].map.call(document.querySelectorAll('.sidebar .ni'), function(e){ return e.textContent.trim(); })")
            for want in ('Home', 'Punch', 'Money', 'Phone book', 'Sync'):
                ok(want in side, 'Mac menu says "%s"' % want)
            for old in ('Dashboard', 'Punchlist', 'Finance', 'Contacts', 'Sync Settings'):
                ok(old not in side, 'old Mac name "%s" is gone' % old)
            ok(not await pg.evaluate("/GitHub Gist/.test(document.body.innerText)"), 'no leftover "GitHub Gist" wording')
            ok(not errs, 'no script errors ' + str(errs[:3]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
