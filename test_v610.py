"""BuildersPro v6.1.0 (BSP phase 1: intake gate, client contact, signed contract + CO gates,
BSP checklist card, pick-two pie on estimates). Run from repo root: python3 test_v610.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
    else: print('  ok  ', m)

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8793', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page()
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            dialogs = []
            answer = {'v': True}
            async def on_dialog(d):
                dialogs.append(d.message)
                await (d.accept() if answer['v'] else d.dismiss())
            pg.on('dialog', lambda d: asyncio.ensure_future(on_dialog(d)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8793/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION") >= '6.1.0', 'version is 6.1.0+')

            # ---- 1. intake gate: missing fields -> Cancel keeps the job unsaved ----
            await pg.evaluate("openAddJob()"); await pg.wait_for_timeout(300)
            await pg.evaluate("document.getElementById('aj-name').value='Lee Bath';document.getElementById('aj-client').value='Ann Lee';document.getElementById('aj-address').value='12 Elm St'")
            n0 = await pg.evaluate("DB.jobs.length")
            answer['v'] = False; dialogs.clear()
            await pg.evaluate("saveJob()"); await pg.wait_for_timeout(400)
            ok(any('email and cell' in d for d in dialogs), 'BSP names the missing email and cell: ' + str(dialogs[-1:]))
            ok(await pg.evaluate("DB.jobs.length") == n0, 'Cancel = job not saved')
            # add the missing fields -> no prompt, job + client contact saved
            await pg.evaluate("document.getElementById('aj-client-email').value='ann@x.com';document.getElementById('aj-client-phone').value='201-555-0100'")
            dialogs.clear(); answer['v'] = True
            await pg.evaluate("saveJob()"); await pg.wait_for_timeout(500)
            ok(not dialogs, 'complete intake saves without a prompt')
            ok(await pg.evaluate("DB.jobs.length") == n0 + 1, 'job saved')
            jid = await pg.evaluate("DB.jobs[DB.jobs.length-1].id")
            c = await pg.evaluate("(DB.contacts||[]).find(c=>c.type==='Client'&&c.jobId==='%s')" % jid)
            ok(c and c['name'] == 'Ann Lee' and c['email'] == 'ann@x.com' and c['phone'] == '201-555-0100' and '12 Elm St' in c['address'], 'client added to contacts: ' + str(c and {k: c[k] for k in ('name','email','phone','address')}))
            # missing + OK saves anyway
            await pg.evaluate("openAddJob()"); await pg.wait_for_timeout(300)
            await pg.evaluate("document.getElementById('aj-name').value='Quick Job'")
            dialogs.clear(); answer['v'] = True
            await pg.evaluate("saveJob()"); await pg.wait_for_timeout(400)
            ok(any('client name, address, email and cell' in d for d in dialogs), 'all four named when empty')
            ok(await pg.evaluate("DB.jobs.some(j=>j.name==='Quick Job')"), 'OK = saved anyway')
            ok(not await pg.evaluate("(DB.contacts||[]).some(c=>c.type==='Client'&&c.jobId===DB.jobs.find(j=>j.name==='Quick Job').id)"), 'no blank client card made when there is no client name')

            # ---- 5. BSP checklist on the job page ----
            await pg.evaluate("openJobDetail('%s')" % jid); await pg.wait_for_timeout(600)
            card = await pg.evaluate("document.getElementById('bsp-ready')?.innerText||''")
            ok('1 to do' in card and 'Signed contract' in card, 'card shows 1 to do (signed contract): ' + card.replace('\n', ' | ')[:160])
            pos = await pg.evaluate("""()=>{var h=document.querySelector('#s-job-detail .detail-header');return h.nextElementSibling&&h.nextElementSibling.id}""")
            ok(pos == 'bsp-ready', 'card sits right under the job header')
            red = await pg.evaluate("""()=>[...document.querySelectorAll('#bsp-ready span')].some(s=>s.style.background==='rgb(255, 69, 58)')""")
            ok(red, 'open item shows a red dot')
            await pg.screenshot(path='/tmp/v610_card.png')

            # ---- 3. signed contract gate ----
            answer['v'] = False; dialogs.clear()
            await pg.evaluate("toggleJobStarted('%s')" % jid); await pg.wait_for_timeout(300)
            ok(any('no signed contract' in d for d in dialogs), 'starting without a contract asks first')
            ok(not await pg.evaluate("DB.jobs.find(j=>j.id==='%s').startDate" % jid), 'Cancel = not started')
            # file a contract document, then start: no prompt
            await pg.evaluate("bspAddSignedContract('%s')" % jid); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("document.getElementById('doc-category').value") == 'Contract', 'Add opens the document sheet set to Contract')
            await pg.evaluate("closeSheet('sheet-add-document');DB.documents=DB.documents||[];DB.documents.push({id:'d1',jobId:'%s',name:'Signed contract',category:'Contract',created:new Date().toISOString()});save()" % jid)
            dialogs.clear()
            await pg.evaluate("toggleJobStarted('%s')" % jid); await pg.wait_for_timeout(300)
            ok(not dialogs, 'with a contract on file, start goes straight through')
            ok(bool(await pg.evaluate("DB.jobs.find(j=>j.id==='%s').startDate" % jid)), 'job started')
            await pg.evaluate("openJobDetail('%s')" % jid); await pg.wait_for_timeout(400)
            card = await pg.evaluate("document.getElementById('bsp-ready')?.innerText||''")
            ok('BSP all set' in card and 'Signed contract' not in card, 'all done = just a small "BSP all set" tag: ' + card.replace('\n', ' | '))

            await pg.evaluate("bspPeek('%s')" % jid); await pg.wait_for_timeout(300)
            ok('Signed contract' in await pg.evaluate("document.getElementById('bsp-ready')?.innerText||''"), 'tapping the tag shows the six checks')
            await pg.evaluate("openJobDetail('%s')" % jid); await pg.wait_for_timeout(300)

            # ---- 4. signed change order gate ----
            await pg.evaluate("openNewChangeOrder('%s')" % jid); await pg.wait_for_timeout(500)
            await pg.evaluate("document.getElementById('co-title').value='Extra vanity';document.getElementById('co-amount').value='900';document.getElementById('co-status').value='Approved'")
            nco = await pg.evaluate("(DB.changeOrders||[]).length")
            await pg.evaluate("saveChangeOrder()"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("(DB.changeOrders||[]).length") == nco, 'Approved without a signature is blocked')
            ok(await pg.evaluate("!!document.getElementById('co-modal')"), 'sheet stays open to sign')
            await pg.evaluate("document.getElementById('co-status').value='Submitted'")
            await pg.evaluate("saveChangeOrder()"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("(DB.changeOrders||[]).length") == nco + 1, 'Submitted (unsigned) still saves')
            # an old approved-but-unsigned CO shows red on the card
            await pg.evaluate("DB.changeOrders.push({id:'old1',jobId:'%s',number:'CO-7',title:'Old',amount:100,status:'Approved'});save();openJobDetail('%s')" % (jid, jid)); await pg.wait_for_timeout(400)
            card = await pg.evaluate("document.getElementById('bsp-ready')?.innerText||''")
            ok('Signed change orders' in card and '1 to do' in card, 'unsigned approved CO is flagged: ' + card.replace('\n', ' | ')[:120])

            # ---- edit job keeps the client card in step ----
            await pg.evaluate("openEditJob('%s')" % jid); await pg.wait_for_timeout(400)
            await pg.evaluate("document.getElementById('ej-client-phone').value='201-555-0199'")
            dialogs.clear()
            await pg.evaluate("saveEditJob('%s')" % jid); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("DB.contacts.filter(c=>c.type==='Client'&&c.jobId==='%s').length" % jid) == 1, 'still one client card (updated, not duplicated)')
            ok(await pg.evaluate("DB.contacts.find(c=>c.type==='Client'&&c.jobId==='%s').phone" % jid) == '201-555-0199', 'client card has the new cell')

            # ---- job isolation: other job's open items never show ----
            other = await pg.evaluate("DB.jobs.find(j=>j.name==='Quick Job').id")
            await pg.evaluate("openJobDetail('%s')" % jid); await pg.wait_for_timeout(300)
            card = await pg.evaluate("document.getElementById('bsp-ready')?.innerText||''")
            ok('Quick Job' not in card, 'card only shows this job')

            # ---- 6. pick-two pie on estimates ----
            await pg.evaluate("openNewEstimate()"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("!!document.getElementById('bsp-pick2')"), 'estimate sheet has the pick-two pie')
            above_notes = await pg.evaluate("document.getElementById('bsp-pick2').nextElementSibling.contains(document.getElementById('est-notes'))")
            ok(above_notes, 'pie sits just above Notes')
            await pg.evaluate("document.getElementById('est-title').value='Kitchen';document.getElementById('est-client').value='Bo Diaz';_estLineItems=[{desc:'Cabinets',qty:1,price:10000}];renderEstItemsRows()")
            await pg.fill('#p2-basedays', '20'); await pg.wait_for_timeout(200)
            vals = await pg.evaluate("['fg','gc','fc'].map(k=>[document.getElementById('p2-price-'+k).value,document.getElementById('p2-days-'+k).value])")
            ok(vals == [['12000', '15'], ['10000', '26'], ['9000', '15']], 'BSP suggests price + days per combo: ' + str(vals))
            # edit one -> line change doesn't overwrite it
            await pg.fill('#p2-price-fg', '12500')
            await pg.evaluate("bpEstUpdateLine(0,'price',11000)"); await pg.wait_for_timeout(200)
            vals2 = await pg.evaluate("['fg','gc'].map(k=>document.getElementById('p2-price-'+k).value)")
            ok(vals2 == ['12500', '11000'], 'edited price is kept, others follow the total: ' + str(vals2))
            # tap slices: only two allowed
            for k in ('fast', 'good', 'cheap'):
                await pg.locator('#p2-s-' + k).tap(force=True); await pg.wait_for_timeout(120)
            msg = await pg.evaluate("document.getElementById('p2-msg').textContent")
            ok('Only 2' in msg, 'third tap is refused: ' + msg)
            fill = await pg.evaluate("document.getElementById('p2-s-fast').getAttribute('stroke')")
            ok(fill == '#30D158', 'picked slice turns green')
            await pg.screenshot(path='/tmp/v610_pie.png')
            await pg.evaluate("saveEstimateModal()"); await pg.wait_for_timeout(400)
            est = await pg.evaluate("DB.estimates[DB.estimates.length-1]")
            ok(sorted(est.get('pick', [])) == ['fast', 'good'], 'pick saved on the estimate: ' + str(est.get('pick')))
            ok(est['pickOptions']['fg']['price'] == 12500 and est['baseDays'] == 20, 'edited option + schedule saved')
            await pg.evaluate("setJobsTab('estimates')"); await pg.wait_for_timeout(300)
            ok('Client pick: Fast + Good' in await pg.evaluate("document.getElementById('estimates-list').innerText"), 'estimate card shows the client pick')
            # reopen keeps state
            await pg.evaluate("openEditEstimate('%s')" % est['id']); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("document.getElementById('p2-price-fg').value") == '12500', 'reopened estimate keeps the edited price')
            ok(await pg.evaluate("document.getElementById('p2-s-good').getAttribute('stroke')") == '#30D158', 'reopened estimate keeps the pick')
            await pg.evaluate("document.getElementById('estimate-modal').remove()")
            # email carries the options + guarantee line
            body = await pg.evaluate("""()=>{var out='';var s=window.sendEmail;window.sendEmail=function(t,su,b){out=b};try{emailEstimate('%s')}finally{window.sendEmail=s}return out}""" % est['id'])
            ok('[x] Fast + Good' in body and 'same on every option' in body and '$12,500' in body, 'estimate email lists the options and the pick')
            # convert -> contract = picked price, client card made
            await pg.evaluate("convertEstimateToJob('%s')" % est['id']); await pg.wait_for_timeout(500)
            job = await pg.evaluate("DB.jobs.find(j=>j.id===DB.estimates.find(e=>e.id==='%s').convertedJobId)" % est['id'])
            ok(job and float(job['contract']) == 12500 and job.get('pick') == 'Fast + Good', 'converted job: contract = picked price, pick stored')
            ok(await pg.evaluate("DB.contacts.some(c=>c.type==='Client'&&c.jobId==='%s'&&c.name==='Bo Diaz')" % job['id']), 'converted job adds the client to contacts')
            # old estimate without pick data still works
            await pg.evaluate("DB.estimates.push({id:'oldE',title:'Old',status:'Draft',lineItems:[{desc:'x',qty:1,price:5}]});save();renderEstimates()")
            ok('Old' in await pg.evaluate("document.getElementById('estimates-list').innerText"), 'older estimates still render')

            ok(not errs, 'no page errors: ' + str(errs[:3]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
