"""BuildersPro — the job flow, step by step, through the app's own screens (iPhone size):
create a job → job details → space + room checklist → punch list → photos → notes →
purchases (shopping list) → expenses, then the totals, then bad / empty input at every step.
Finally the Mac (Command Center) must show the same totals for the same data.
Run from repo root: python3 test_v622_job_flow.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json, base64, io
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8895
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

def jpeg(seed):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (1200, 900), (seed * 50 % 255, 90, 160)); ImageDraw.Draw(im).text((30, 30), 'site %d' % seed, fill=(255, 255, 255))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=85); return base64.b64encode(b.getvalue()).decode()

FILES = """(b64s) => b64s.map(function(b, i){ var bin = atob(b), u = new Uint8Array(bin.length); for (var k = 0; k < bin.length; k++) u[k] = bin.charCodeAt(k);
  return new File([u], 'site' + i + '.jpg', { type: 'image/jpeg' }); })"""

async def boot(pg):
    await pg.wait_for_timeout(2800)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    pics = [jpeg(i) for i in range(3)]
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            dialogs = []
            async def dlg(d): dialogs.append(d.message); await d.accept()
            pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await boot(pg)
            await pg.evaluate("DB.jobs = []; DB.rooms = []; DB.punchlist = []; DB.photos = []; DB.jobNotes = []; DB.shopping = []; DB.expenses = []; DB.invoices = []; DB.contractors = []; DB.payments = []; save();")

            print('\n1. Create and save a job')
            await pg.evaluate("openSheet('sheet-add-job')"); await pg.wait_for_timeout(300)
            await pg.evaluate("saveJob()"); await pg.wait_for_timeout(200)
            ok(any('Job name required' in d for d in dialogs) and await pg.evaluate("DB.jobs.length") == 0, 'empty job name is refused, nothing saved')
            fill = {'aj-name': 'n. peach st', 'aj-client': 'shelden washington', 'aj-client-email': 'sw@example.com', 'aj-client-phone': '8626869866',
                    'aj-address': '1536 n. peach st', 'aj-city': 'philadelphia', 'aj-state': 'pa', 'aj-zip': '19131', 'aj-contract': '45000'}
            for k, v in fill.items(): await pg.evaluate("([k, v]) => { var e = document.getElementById(k); if (e) e.value = v; }", [k, v])
            await pg.evaluate("saveJob()"); await pg.wait_for_timeout(300)
            j = await pg.evaluate("DB.jobs[0] || null")
            ok(j is not None and await pg.evaluate("DB.jobs.length") == 1, 'job saved once')
            jid = j['id'] if j else ''
            ok(j and j['name'] == 'N. Peach St' and j['client'] == 'Shelden Washington' and j['city'] == 'Philadelphia' and j['state'] == 'PA', 'names and city capitalized, state upper-case')
            ok(j and float(j['contract']) == 45000, 'contract amount kept ($45,000)')
            ok(await pg.evaluate("(id) => (DB.contacts||[]).some(function(c){ return c.type === 'Client' && c.jobId === id && c.name === 'Shelden Washington'; })", jid), 'client added to the phone book')
            await pg.reload(); await boot(pg)
            ok(await pg.evaluate("(id) => DB.jobs.some(function(j){ return j.id === id; })", jid), 'job still there after closing and reopening the app')

            print('\n2. Job details')
            await pg.evaluate("(id) => openJobDetail(id)", jid); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("document.querySelector('#s-job-detail.active') !== null || (document.getElementById('s-job-detail')||{}).offsetParent !== null"), 'job page opens')
            body = await pg.inner_text('#s-job-detail')
            ok('N. Peach St' in body and 'Shelden Washington' in body, 'job page shows the job and client')
            ok(await pg.evaluate("bpActiveJob()") == jid, 'opening the job makes it the job you are on')

            print('\n3. Space and room checklist')
            await pg.evaluate("openSheet('sheet-add-room')"); await pg.wait_for_timeout(250)
            await pg.evaluate("document.getElementById('ar-name').value = ''; saveRoom();"); await pg.wait_for_timeout(200)
            ok(any('Space name required' in d for d in dialogs) and await pg.evaluate("(DB.rooms||[]).length") == 0, 'empty space name is refused')
            await pg.evaluate("(id) => { document.getElementById('ar-name').value = '(B) Bathroom'; var t = document.getElementById('ar-type'); t.value = 'Bathroom'; var jb = document.getElementById('ar-job'); if (![].some.call(jb.options, function(o){ return o.value === id; })) { var o = document.createElement('option'); o.value = id; jb.appendChild(o); } jb.value = id; saveRoom(); }", jid)
            await pg.wait_for_timeout(700)
            room = await pg.evaluate("(DB.rooms||[])[0] || null")
            rid = room['id'] if room else ''
            ok(room and room['name'] == '(B) Bathroom' and room['jobId'] == jid, 'space saved on the job')
            ok(await pg.evaluate("(document.getElementById('sheet-add-punch')||{}).classList && document.getElementById('sheet-add-punch').classList.contains('open')"), 'adding a space goes straight to its checklist')
            await pg.evaluate("bpPunchCatMenu()"); await pg.wait_for_timeout(150)   # categories sit behind the "Choose a category" menu
            cats = await pg.evaluate("[].map.call(document.querySelectorAll('#pa-cats button'), function(b){ return b.textContent.trim(); }).filter(function(t){ return t && !/choose a category/i.test(t); })")
            cat = 'Plumbing' if any('Plumbing' in c for c in cats) else (cats[0] if cats else 'Plumbing')
            ok(len(cats) >= 3, 'category menu lists trades (%s)' % ', '.join(cats[:6]))
            await pg.evaluate("(c) => { bpPunchCat(c); bpPunchTplToggle(); }", cat); await pg.wait_for_timeout(200)
            tpl = await pg.evaluate("[].map.call(document.querySelectorAll('#pa-tpl label span'), function(s){ return s.textContent; })")
            ok(len(tpl) >= 3, '%s checklist offered for a bathroom (%d items)' % (cat, len(tpl)))
            for i in range(min(3, len(tpl))): await pg.evaluate("(i) => bpPunchTpl(i)", i)
            n = await pg.evaluate("(r) => DB.punchlist.filter(function(p){ return p.roomId === r; }).length", rid)
            ok(n == min(3, len(tpl)), 'checking items adds them to the space (%d)' % n)
            await pg.evaluate("bpPunchTpl(0)")
            ok(await pg.evaluate("(r) => DB.punchlist.filter(function(p){ return p.roomId === r; }).length", rid) == n - 1, 'unchecking removes it again')
            await pg.evaluate("bpPunchTpl(0)")

            print('\n4. Punch list')
            await pg.evaluate("bpPunchCommit()")
            before = await pg.evaluate("DB.punchlist.length")
            await pg.evaluate("(c) => { bpPunchCat(''); bpPunchCommit(); }", cat)
            ok(await pg.evaluate("DB.punchlist.length") == before, 'a punch item with no category is refused')
            await pg.evaluate("(c) => { bpPunchCat(c); bpPunchNote('vanity drain leaks'); }", cat)
            files = await pg.evaluate_handle(FILES, pics[:1])
            await pg.evaluate("(fs) => bpPunchPick({ files: fs })", files)
            await pg.evaluate("bpPunchCommit()"); await pg.wait_for_timeout(2500)
            it = await pg.evaluate("DB.punchlist.find(function(p){ return /vanity drain leaks/.test(p.text); }) || null")
            ok(it and it['roomId'] == rid and it['trade'] == cat, 'punch item saved in the space with its category')
            ok(it and len(it.get('photosBefore') or []) == 1 and str(it['photosBefore'][0].get('src', it['photosBefore'][0]))[:5] == 'data:', 'punch item keeps its before photo')
            await pg.evaluate("bpPunchDone && bpPunchDone()")
            total = await pg.evaluate("(id) => jobProgress(id)", jid)
            await pg.evaluate("(r) => { var L = DB.punchlist.filter(function(p){ return p.roomId === r; }); toggleChecklistItem(L[0].id); toggleChecklistItem(L[1].id); }", rid)
            await pg.wait_for_timeout(300)
            pr = await pg.evaluate("(id) => jobProgress(id)", jid)
            ok(pr['done'] == 2 and pr['total'] == total['total'] and pr['pct'] == round(2 / pr['total'] * 100), 'checking off 2 items: %d of %d done, %d%%' % (pr['done'], pr['total'], pr['pct']))
            await pg.evaluate("(r) => { var L = DB.punchlist.filter(function(p){ return p.roomId === r; }); toggleChecklistItem(L[1].id); }", rid); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("(id) => jobProgress(id).done", jid) == 1, 'un-checking puts it back to open')
            ok(await pg.evaluate("(r) => !!DB.punchlist.filter(function(p){ return p.roomId === r; })[0].completedAt", rid), 'a done item records when it was finished')

            print('\n5. Photos')
            files = await pg.evaluate_handle(FILES, pics[1:3])
            await pg.evaluate("([fs, id]) => addPhotos({ files: fs }, id)", [files, jid]); await pg.wait_for_timeout(3500)
            ph = await pg.evaluate("(id) => DB.photos.filter(function(p){ return p.jobId === id; }).map(function(p){ return { len: p.src.length, data: p.src.slice(0,5) === 'data:', date: !!p.date }; })", jid)
            ok(len(ph) == 2 and all(x['data'] and x['date'] for x in ph), 'two photos saved on the job with their date')
            ok(all(x['len'] < 900000 for x in ph), 'photos are compressed (largest %d KB)' % (max(x['len'] for x in ph) // 1024 if ph else 0))
            n0 = await pg.evaluate("DB.photos.length")
            bad = await pg.evaluate_handle("() => [new File([new Uint8Array([1,2,3])], 'notes.txt', { type: 'text/plain' })]")
            await pg.evaluate("([fs, id]) => addPhotos({ files: fs }, id)", [bad, jid]); await pg.wait_for_timeout(800)
            ok(await pg.evaluate("DB.photos.length") == n0, 'a file that is not a picture is ignored')

            print('\n6. Notes')
            await pg.evaluate("(id) => bpNoteEdit(null, id)", jid); await pg.wait_for_timeout(300)
            saved = await pg.evaluate("""() => { var t = document.getElementById('bpn-text'); if (!t) return 'no box'; t.value = 'Customer wants matte black fixtures';
              var b = [].slice.call(document.querySelectorAll('#bp-notes-ov button')).find(function(x){ return /save/i.test(x.textContent); }); if (!b) return 'no save'; b.click(); return 'ok'; }""")
            await pg.wait_for_timeout(400)
            nt = await pg.evaluate("(id) => (DB.jobNotes||[]).filter(function(n){ return n.jobId === id; })", jid)
            ok(saved == 'ok' and len(nt) == 1 and 'matte black' in nt[0].get('text', ''), 'note saved on the job')
            ok(nt and bool(nt[0].get('created')), 'note is dated')
            await pg.evaluate("(id) => bpNoteEdit(null, id)", jid); await pg.wait_for_timeout(300)
            await pg.evaluate("() => { var b = [].slice.call(document.querySelectorAll('#bp-notes-ov button')).find(function(x){ return /save/i.test(x.textContent); }); if (b) b.click(); }")
            await pg.wait_for_timeout(300)
            ok(await pg.evaluate("(id) => (DB.jobNotes||[]).filter(function(n){ return n.jobId === id; }).length", jid) == 1, 'an empty note is not saved')
            await pg.evaluate("var o = document.getElementById('bp-notes-ov'); if (o) o.remove();")

            print('\n7. Purchases (shopping list)')
            await pg.evaluate("(id) => { bpOpenShop(id); bpShopOpenAdd(); }", jid); await pg.wait_for_timeout(300)
            async def add_item(text, qty, price):
                await pg.evaluate("([t, q, p]) => { var s = function(k, v){ var e = document.getElementById('bp-sa-' + k); if (e) e.value = v; }; s('text', t); s('qty', q); s('price', p); bpShopSaveNew(true); }", [text, qty, price])
                await pg.wait_for_timeout(150)
            n0 = await pg.evaluate("(DB.shopping||[]).length")
            await add_item('', '2', '10')
            ok(await pg.evaluate("(DB.shopping||[]).length") == n0, 'an item with no name is refused')
            await add_item('1/2" PEX', 'abc', '10')
            ok(await pg.evaluate("(DB.shopping||[]).length") == n0, 'a quantity that is not a number is refused')
            await add_item('Elbows', '-3', '2')
            ok(await pg.evaluate("(DB.shopping||[]).length") == n0, 'a negative quantity is refused')
            await add_item('Elbows', '3', '-2')
            ok(await pg.evaluate("(DB.shopping||[]).length") == n0, 'a negative price is refused')
            await add_item('1/2" PEX', '2', '49.99')
            await add_item('Elbows', '10', '1.25')
            await add_item('Shut-off valve', '3*2', '12.10')
            t = await pg.evaluate("(id) => bpShopTotals(id)", jid)
            exp = 2 * 49.99 + 10 * 1.25 + 6 * 12.10
            ok(abs(t['toBuy'] - exp) < 0.001 and t['nOpen'] == 3, 'to-buy total $%.2f for 3 items (math in quantity: 3*2 = 6)' % t['toBuy'])
            ok(abs(t['tax'] - round(exp * t['rate']) / 100) < 0.011 and abs(t['toBuyWithTax'] - (exp + t['tax'])) < 0.001, 'tax at %s%% = $%.2f, total with tax $%.2f' % (t['rate'], t['tax'], t['toBuyWithTax']))
            await pg.evaluate("(id) => { var x = DB.shopping.find(function(s){ return s.jobId === id && s.text === 'Elbows'; }); x.bought = true; x.updatedAt = new Date().toISOString(); save(); }", jid)
            t2 = await pg.evaluate("(id) => bpShopTotals(id)", jid)
            ok(abs(t2['bought'] - 12.5) < 0.001 and abs(t2['toBuy'] - (exp - 12.5)) < 0.001 and abs(t2['all'] - exp) < 0.001, 'buying an item moves $12.50 from to-buy to bought, total unchanged')
            await pg.evaluate("var o = document.getElementById('bp-shop-new'); if (o) o.remove(); var s = document.getElementById('bp-shop'); if (s) s.remove();")

            print('\n8. Expenses')
            async def add_exp(desc, amount, cat='Materials'):
                await pg.evaluate("openSheet('sheet-add-expense')"); await pg.wait_for_timeout(200)
                await pg.evaluate("([d, a, c, id]) => { var s = function(k, v){ var e = document.getElementById(k); if (e) e.value = v; }; s('exp-desc', d); s('exp-amount', a); s('exp-cat', c);"
                                  " var jb = document.getElementById('exp-job'); if (jb && ![].some.call(jb.options, function(o){ return o.value === id; })) { var o = document.createElement('option'); o.value = id; jb.appendChild(o); } if (jb) jb.value = id; saveExpense(); }", [desc, amount, cat, jid])
                await pg.wait_for_timeout(200)
            n0 = await pg.evaluate("(DB.expenses||[]).length")
            await add_exp('', '25')
            ok(await pg.evaluate("(DB.expenses||[]).length") == n0, 'an expense with no description is refused')
            await add_exp('Fittings', '')
            ok(await pg.evaluate("(DB.expenses||[]).length") == n0, 'an expense with no amount is refused')
            await add_exp('Fittings', '-25')
            ok(await pg.evaluate("(DB.expenses||[]).length") == n0, 'a negative amount is refused')
            await add_exp('Fittings', '0')
            ok(await pg.evaluate("(DB.expenses||[]).length") == n0, 'a $0 amount is refused')
            await add_exp('Home Depot run', '10.10')
            await add_exp('Dump fee', '20.20', 'Other')
            ex = await pg.evaluate("(id) => (DB.expenses||[]).filter(function(e){ return e.jobId === id; })", jid)
            ok(len(ex) == 2 and abs(sum(e['amount'] for e in ex) - 30.30) < 0.001 and all(isinstance(e['amount'], (int, float)) for e in ex), 'two expenses saved as numbers, $30.30 together')
            await pg.evaluate("(id) => { DB.contractors.push({ id:'c1', jobId:id, name:'Ever', trade:'Plumbing' }); DB.payments.push({ id:'pay1', contractorId:'c1', amount:1650, date:'2026-10-20' }, { id:'pay2', contractorId:'c1', amount:350, date:'2026-10-22' });"
                              " DB.invoices.push({ id:'in1', jobId:id, number:'1', amount:5000, status:'Paid' }, { id:'in2', jobId:id, number:'2', amount:2500, status:'Sent' }); save(); }", jid)
            f = await pg.evaluate("(id) => jobFunding(id)", jid)
            ok(f['contract'] == 45000 and f['received'] == 5000 and f['owed'] == 40000, 'received $5,000 (only Paid invoices), balance owed $40,000')
            await pg.evaluate("(id) => { showScreen('s-finance'); var s = document.getElementById('finance-job-filter'); if (s) { s.value = id; } try { if (typeof switchFinanceTab === 'function') switchFinanceTab('spending'); } catch(e){} renderFinance(); }", jid)
            await pg.wait_for_timeout(500)
            el = await pg.evaluate("(id) => { var d = document.createElement('div'); renderSpendingTab(d, id); return d.innerText; }", jid)
            ok('$2,030.30' in el, 'Total Spent = expenses $30.30 + sub payments $2,000 = $2,030.30')
            ok('$30.30' in el, 'expenses shown as $30.30 (cents always shown)')

            print('\n9. Same totals on the Mac')
            data = await pg.evaluate("JSON.stringify({ jobs: DB.jobs, rooms: DB.rooms, punchlist: DB.punchlist, expenses: DB.expenses, invoices: DB.invoices, contractors: DB.contractors, payments: DB.payments, shopping: DB.shopping, changeOrders: DB.changeOrders || [] })")
            mac = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page()
            await mac.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await mac.goto('http://localhost:%d/desktop.html' % PORT); await boot(mac)
            await mac.evaluate("(s) => { var o = JSON.parse(s); Object.keys(o).forEach(function(k){ DB[k] = o[k]; }); saveDB(); }", data)
            mf = await mac.evaluate("(id) => jobFunding(id)", jid)
            ok(mf == f, 'Mac: same contract / received / owed (%s)' % json.dumps(mf))
            mp = await mac.evaluate("(id) => jobProgress(id)", jid)
            ok(mp == pr or (mp['total'] == pr['total'] and mp['done'] == 1), 'Mac: same punch progress (%s)' % json.dumps(mp))
            mt = await mac.evaluate("(id) => typeof bpShopTotals === 'function' ? bpShopTotals(id) : null", jid)
            ok(mt is not None and abs(mt['toBuy'] - t2['toBuy']) < 0.001 and abs(mt['bought'] - t2['bought']) < 0.001, 'Mac: same shopping totals')

            print('\n10. Same input checks on the Mac')
            msgs = []
            mac.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            async def mac_exp(desc, amount):
                await mac.evaluate("([d, a, id]) => { if (typeof openNewExpense === 'function') openNewExpense(); var s = function(k, v){ var e = document.getElementById(k); if (e) e.value = v; }; s('ne-desc', d); s('ne-amount', a);"
                                   " var jb = document.getElementById('ne-job'); if (jb && ![].some.call(jb.options, function(o){ return o.value === id; })) { var o = document.createElement('option'); o.value = id; jb.appendChild(o); } if (jb) jb.value = id;"
                                   " var f = window.saveNewExpense || window.saveExpenseDesktop || window.saveNewExpenseDesktop; if (f) f(); }", [desc, amount, jid])
                await mac.wait_for_timeout(200)
            has = await mac.evaluate("!!document.getElementById('ne-amount') && !!(window.saveNewExpense || window.saveExpenseDesktop || window.saveNewExpenseDesktop)")
            ok(has, 'Mac expense form found')
            if has:
                n0 = await mac.evaluate("DB.expenses.length")
                await mac_exp('Fittings', '-25'); await mac_exp('Fittings', '0')
                ok(await mac.evaluate("DB.expenses.length") == n0, 'Mac: negative and $0 expenses refused')
                await mac_exp('Fittings', '12.5')
                ok(await mac.evaluate("DB.expenses.length") == n0 + 1, 'Mac: a normal expense still saves')
            await mac.evaluate("(id) => { bpOpenShop(id); bpShopOpenAdd(); }", jid); await mac.wait_for_timeout(300)
            n0 = await mac.evaluate("(DB.shopping||[]).length")
            for q, pr in (('-3', '2'), ('3', '-2'), ('0', '2')):
                await mac.evaluate("([q, p]) => { var s = function(k, v){ var e = document.getElementById('bp-sa-' + k); if (e) e.value = v; }; s('text', 'Elbows'); s('qty', q); s('price', p); bpShopSaveNew(true); }", [q, pr])
                await mac.wait_for_timeout(120)
            ok(await mac.evaluate("(DB.shopping||[]).length") == n0, 'Mac: negative / zero quantity and negative price refused')
            fm = await mac.evaluate("[bpMoney(30.3), bpMoney(45000), bpMoney(2030.3), bpMoney(0.1 + 0.2), bpMoney(-12.5)]")
            ok(fm == ['$30.30', '$45,000', '$2,030.30', '$0.30', '-$12.50'], 'money format on the Mac: %s' % fm)
            fp = await pg.evaluate("[bpMoney(30.3), bpMoney(45000), bpMoney(2030.3), bpMoney(0.1 + 0.2), bpMoney(-12.5)]")
            ok(fp == fm, 'money format identical on the iPhone')
            ok(not errs, 'no script errors ' + str(errs[:3]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for x in fails: print('  - ' + x)
    sys.exit(1 if fails else 0)
asyncio.run(main())
