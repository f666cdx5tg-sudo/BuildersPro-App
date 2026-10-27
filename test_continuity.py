"""BuildersPro — pick up where you left off, on any device.

Three devices — iPhone (field app), iPad (field app) and Mac (Command Center) — share ONE
simulated iCloud (same record API the apps use: bp_state + BPChunk pieces, change tags, conflicts).
Each device creates, edits and deletes every kind of record; after syncing, every other device
must hold exactly the same data, photos included, and survive a restart.

Run from repo root:  python3 test_continuity.py      Exit 0 = all pass."""
import subprocess, time, asyncio, json, sys, os, base64, io
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
PORT = 8890
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

# ── one shared iCloud ────────────────────────────────────────────────────────
STORE = {}; TAG = [0]
def ck(payload):
    q = json.loads(payload); op = q['op']
    if op == 'fetch':
        recs = []
        for n in q['names']:
            r = STORE.get(n)
            if r: recs.append(r)
        return json.dumps({'records': recs})
    if op == 'save':
        out, errs = [], []
        for r in q['records']:
            n = r['recordName']; cur = STORE.get(n)
            if r.get('recordType') == 'BPState' and cur and r.get('recordChangeTag') != cur['recordChangeTag']:
                errs.append({'ckErrorCode': 'CONFLICT', 'recordName': n}); continue
            TAG[0] += 1
            rec = {'recordName': n, 'recordType': r.get('recordType'), 'fields': r.get('fields', {}), 'recordChangeTag': 't%d' % TAG[0]}
            STORE[n] = rec; out.append(rec)
        res = {'records': out}
        if errs: res.update(hasErrors=True, errors=errs)
        return json.dumps(res)
    if op == 'delete':
        for n in q['names']: STORE.pop(n, None)
        return json.dumps({'records': []})
    return json.dumps({})

FAKE_CK = """
localStorage.setItem('bp_ck_on','1');
(function(){
  function call(op, o){ o.op = op; return window.ckCall(JSON.stringify(o)).then(JSON.parse); }
  var DBX = {
    fetchRecords: function(names){ return call('fetch', { names: [].concat(names).map(function(n){ return typeof n === 'string' ? n : n.recordName; }) }); },
    saveRecords: function(recs){ return call('save', { records: [].concat(recs) }); },
    deleteRecords: function(names){ return call('delete', { names: [].concat(names) }); }
  };
  var C = { setUpAuth: async function(){ return { userRecordName: 'stan' }; }, whenUserSignsIn: function(){ return new Promise(function(){}); }, privateCloudDatabase: DBX };
  window.CloudKit = { configure: function(){}, getDefaultContainer: function(){ return C; } };
})();
"""

def photo(seed, w=640, h=480):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (seed * 40 % 255, seed * 90 % 255, seed * 150 % 255))
    ImageDraw.Draw(im).text((20, 20), 'photo %d' % seed, fill=(255, 255, 255))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()

DEVICES = [('iPhone', 'index.html', {'width': 390, 'height': 844}, True),
           ('iPad', 'index.html', {'width': 1024, 'height': 1366}, True),
           ('Mac', 'desktop.html', {'width': 1440, 'height': 900}, False)]

# every kind of record, with the fields a real one carries
def records(tag, jid, rid, cid, pic, pic2):
    t = '2026-10-26T12:00:00.000Z'
    return {
      'rooms':        [{'id': 'r_'+tag, 'jobId': jid, 'name': 'Kitchen '+tag, 'type': 'Kitchen', 'level': 'Level 1', 'updatedAt': t}],
      'punchlist':    [{'id': 'p_'+tag, 'jobId': jid, 'roomId': rid, 'text': 'Install vanity '+tag, 'done': False, 'status': 'Open',
                        'photosBefore': [{'src': pic2, 'date': t}], 'photosAfter': [], 'updatedAt': t}],
      'photos':       [{'id': 'ph_'+tag, 'jobId': jid, 'roomId': rid, 'src': pic, 'date': t, 'caption': 'from '+tag, 'updatedAt': t}],
      'tasks':        [{'id': 'tk_'+tag, 'jobId': jid, 'text': 'Call inspector '+tag, 'done': False, 'updatedAt': t}],
      'notes':        [{'id': 'n_'+tag, 'jobId': jid, 'text': 'Note '+tag, 'date': t, 'updatedAt': t}],
      'jobNotes':     [{'id': 'jn_'+tag, 'jobId': jid, 'roomId': rid, 'body': 'Field note '+tag, 'photos': [pic2], 'audio': [], 'created': t, 'updatedAt': t}],
      'expenses':     [{'id': 'e_'+tag, 'jobId': jid, 'desc': 'PEX fittings '+tag, 'amount': 123.45, 'category': 'Materials', 'date': '2026-10-26', 'receiptSrc': pic2, 'updatedAt': t}],
      'invoices':     [{'id': 'i_'+tag, 'jobId': jid, 'number': 'INV-'+tag, 'amount': 5000, 'status': 'Sent', 'date': '2026-10-26', 'updatedAt': t}],
      'contractors':  [{'id': 'c_'+tag, 'jobId': jid, 'name': 'Sub '+tag, 'company': 'Co '+tag, 'phone': '555-0100', 'email': tag+'@x.com', 'trade': 'Electrical', 'contractValue': 2500, 'updatedAt': t}],
      'payments':     [{'id': 'pay_'+tag, 'contractorId': cid, 'jobId': jid, 'amount': 750, 'date': '2026-10-26', 'note': 'draw '+tag, 'updatedAt': t}],
      'appointments': [{'id': 'a_'+tag, 'jobId': jid, 'date': '2026-10-28', 'time': '09:30', 'title': 'Inspection '+tag, 'type': 'Inspection', 'updatedAt': t}],
      'reports':      [{'id': 'rep_'+tag, 'jobId': jid, 'date': '2026-10-26', 'summary': 'EOD '+tag, 'workers': 2, 'updatedAt': t}],
      'contacts':     [{'id': 'ct_'+tag, 'name': 'Contact '+tag, 'phone': '555-0101', 'email': 'c'+tag+'@x.com', 'type': 'Vendor', 'updatedAt': t}],
      'permits':      [{'id': 'pm_'+tag, 'jobId': jid, 'trade': 'Plumbing', 'permitNumber': 'P-'+tag, 'status': 'Applied', 'updatedAt': t}],
      'documents':    [{'id': 'd_'+tag, 'jobId': jid, 'name': 'Contract '+tag, 'category': 'Contract', 'src': pic2, 'date': t, 'updatedAt': t}],
      'estimates':    [{'id': 'est_'+tag, 'jobId': jid, 'client': 'Client '+tag, 'status': 'Draft', 'lines': [{'desc': 'Rough plumbing', 'qty': 1, 'price': 4200}], 'updatedAt': t}],
      'timeEntries':  [{'id': 'te_'+tag, 'jobId': jid, 'start': t, 'end': '2026-10-26T16:00:00.000Z', 'rate': 85, 'updatedAt': t}],
      'changeOrders': [{'id': 'co_'+tag, 'jobId': jid, 'title': 'Extra outlet '+tag, 'amount': 350, 'status': 'Pending', 'updatedAt': t}],
      'shopping':     [{'id': 'sh_'+tag, 'jobId': jid, 'item': '1/2" PEX '+tag, 'qty': 2, 'unit': 'roll', 'price': 49, 'bought': False, 'updatedAt': t}],
      'vendors':      [{'id': 'v_'+tag, 'name': 'Supply house '+tag, 'phone': '555-0102', 'updatedAt': t}],
      'walkthroughs': [{'id': 'w_'+tag, 'jobId': jid, 'date': '2026-10-26', 'notes': 'Walk '+tag, 'updatedAt': t}],
    }

SNAP = """(function(){
  var out = {}, skip = { recycle: 1 };
  bpAllCollections(DB).forEach(function(k){ if (skip[k] || !Array.isArray(DB[k])) return;
    out[k] = DB[k].filter(function(x){ return x && x.id; }).map(function(x){
      var c = JSON.parse(JSON.stringify(x));
      ['src','receiptSrc','photosBefore','photosAfter','photos','completionPhoto'].forEach(function(f){
        if (typeof c[f] === 'string' && c[f].length > 200) c[f] = 'IMG' + c[f].length;
        if (Array.isArray(c[f])) c[f] = c[f].map(function(p){ var s = typeof p === 'string' ? p : (p && p.src); return s && s.length > 200 ? 'IMG' + s.length : p; });
      });
      return c; }).sort(function(a, b){ return a.id < b.id ? -1 : 1; }); });
  out.jobs = (DB.jobs || []).map(function(j){ return { id: j.id, name: j.name, client: j.client, security: j.security, pick: j.pick, status: j.status }; });
  return out; })()"""

async def sync(pg):
    r = await pg.evaluate("(async function(){ var r = await window.bpICloudSync('both'); return { r: r, err: (window.bpCk && bpCk.state.lastErr) || '' }; })()")
    return r

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    pics = {d[0]: (photo(i + 1), photo(i + 11)) for i, d in enumerate(DEVICES)}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pages = {}; errs = {}
            for name, page, vp, touch in DEVICES:
                ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=(name == 'iPhone'))
                await ctx.expose_function('ckCall', ck)
                await ctx.add_init_script(FAKE_CK)
                pg = await ctx.new_page(); errs[name] = []
                pg.on('pageerror', lambda e, n=name: errs[n].append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/%s' % (PORT, page)); await pg.wait_for_timeout(3000)
                await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
                pages[name] = (pg, ctx, page)

            print('\n1. iPhone starts the job in the field')
            ph = pages['iPhone'][0]
            await ph.evaluate("""(function(){ DB.jobs.push({ id: 'job1', name: 'N. Peach St', client: 'Shelden Washington', address: '1536 N. Peach St',
                city: 'Philadelphia', state: 'PA', zip: '19131', clientEmail: 'sw@example.com', clientPhone: '862-686-9866', contract: 45000, status: 'Active',
                security: [{ id: 's1', kind: 'door', label: 'Lockbox', secret: '4471' }], pick: ['fast', 'good'], updatedAt: new Date().toISOString() }); bpSave(); })()""")
            r = await sync(ph); ok(not r['err'], 'iPhone first sync clean ' + r['err'])

            print('\n2. every device adds every kind of record, then syncs')
            for name in ('iPhone', 'iPad', 'Mac'):
                pg = pages[name][0]
                r = await sync(pg)   # pull first, like opening the app
                ok(not r['err'], name + ' pull clean ' + r['err'])
                recs = records(name, 'job1', 'r_' + name, 'c_' + name, *pics[name])
                await pg.evaluate("(R) => { Object.keys(R).forEach(function(k){ if (!Array.isArray(DB[k])) DB[k] = []; R[k].forEach(function(x){ x.updatedAt = new Date().toISOString(); DB[k].push(x); }); }); bpSave(); }", recs)
                r = await sync(pg); ok(not r['err'], name + ' push clean ' + r['err'])
            for name in ('iPhone', 'iPad', 'Mac'):
                r = await sync(pages[name][0]); ok(not r['err'], name + ' second round clean ' + r['err'])
            snaps = {n: await pages[n][0].evaluate(SNAP) for n in pages}
            kinds = list(records('x', 'j', 'r', 'c', 'a', 'b').keys())
            for n in snaps:   # v2.33: the old notes list is converted into punch items everywhere
                ok(all(any(x['id'] == 'mig_n_' + d for x in snaps[n].get('punchlist', [])) for d in ('iPhone', 'iPad', 'Mac')) and not snaps[n].get('notes'),
                   n + ': old-style notes became punch items (mig_…) and the old list is empty')
            for k in [k for k in kinds if k != 'notes']:
                ids = {n: sorted(x['id'] for x in snaps[n].get(k, [])) for n in snaps}
                want = sorted(k_ + '_' + d for d in ('iPhone', 'iPad', 'Mac') for k_ in [records('x', 'j', 'r', 'c', 'a', 'b')[k][0]['id'].split('_')[0]])
                same = ids['iPhone'] == ids['iPad'] == ids['Mac']
                ok(same and all(w in ids['Mac'] for w in want), '%-13s same on iPhone, iPad and Mac (%d each)' % (k, len(ids['Mac'])))
            ok(json.dumps(snaps['iPhone'], sort_keys=True) == json.dumps(snaps['Mac'], sort_keys=True) == json.dumps(snaps['iPad'], sort_keys=True),
               'every field of every record identical on all three')
            j = snaps['Mac']['jobs'][0] if snaps['Mac']['jobs'] else {}
            ok(j.get('security') and j['security'][0]['secret'] == '4471', 'job Security codes reach the Mac')
            ok(j.get('pick') == ['fast', 'good'], 'fast/good/cheap pick reaches the Mac')
            for name in pages:
                n = await pages[name][0].evaluate("(DB.photos||[]).filter(function(p){ return typeof p.src === 'string' && p.src.slice(0,5) === 'data:' && p.src.length > 1000; }).length")
                ok(n == 3, name + ': all 3 photos have their real picture (%d)' % n)

            print('\n3. edit on one device, keep going on another')
            await pages['Mac'][0].evaluate("(function(){ var x = DB.punchlist.find(function(p){ return p.id === 'p_iPhone'; }); x.done = true; x.status = 'Done'; x.updatedAt = new Date().toISOString(); bpSave(); })()")
            await sync(pages['Mac'][0])
            await pages['iPad'][0].evaluate("(function(){ var x = DB.expenses.find(function(p){ return p.id === 'e_Mac'; }); x.amount = 999.99; x.updatedAt = new Date().toISOString(); bpSave(); })()")
            await sync(pages['iPad'][0])
            for name in ('iPhone', 'iPad', 'Mac'): await sync(pages[name][0])
            for name in pages:
                v = await pages[name][0].evaluate("({ done: DB.punchlist.find(function(p){ return p.id === 'p_iPhone'; }).done, amt: DB.expenses.find(function(p){ return p.id === 'e_Mac'; }).amount })")
                ok(v['done'] is True and v['amt'] == 999.99, name + ': sees the Mac check-off and the iPad price change')

            print('\n4. same item edited on two devices — newest edit wins everywhere')
            await pages['iPhone'][0].evaluate("(function(){ var x = DB.tasks.find(function(p){ return p.id === 'tk_Mac'; }); x.text = 'older edit'; x.updatedAt = new Date(Date.now() + 60000).toISOString(); bpSave(); })()")
            await pages['Mac'][0].evaluate("(function(){ var x = DB.tasks.find(function(p){ return p.id === 'tk_Mac'; }); x.text = 'newer edit'; x.updatedAt = new Date(Date.now() + 120000).toISOString(); bpSave(); })()")
            for name in ('iPhone', 'Mac', 'iPad', 'iPhone'): await sync(pages[name][0])
            for name in pages:
                t = await pages[name][0].evaluate("DB.tasks.find(function(p){ return p.id === 'tk_Mac'; }).text")
                ok(t == 'newer edit', name + ': newest edit kept (' + t + ')')

            print('\n5. delete on one device — gone everywhere, restorable')
            await pages['iPad'][0].evaluate("bpRemoveFrom('photos', function(p){ return p.id !== 'ph_iPhone'; }); bpRemoveFrom('payments', function(p){ return p.id !== 'pay_Mac'; }); bpSave();")
            for name in ('iPad', 'iPhone', 'Mac'): await sync(pages[name][0])
            for name in pages:
                v = await pages[name][0].evaluate("({ ph: DB.photos.some(function(p){ return p.id === 'ph_iPhone'; }), pay: DB.payments.some(function(p){ return p.id === 'pay_Mac'; }) })")
                ok(not v['ph'] and not v['pay'], name + ': deleted photo and payment are gone')
            v = await pages['iPad'][0].evaluate("(DB.recycle||[]).filter(function(e){ return e.id === 'rc_photos_ph_iPhone' || e.id === 'rc_payments_pay_Mac'; }).length")
            ok(v == 2, 'both are in Recently Deleted on the device that deleted them')
            await pages['iPad'][0].evaluate("bpRestore('rc_photos_ph_iPhone', true); bpSave();")
            for name in ('iPad', 'iPhone', 'Mac'): await sync(pages[name][0])
            for name in pages:
                v = await pages[name][0].evaluate("DB.photos.some(function(p){ return p.id === 'ph_iPhone'; })")
                ok(v, name + ': restored photo is back')

            print('\n6. where you left off — the job you are working on follows you')
            await ph.evaluate("bpSetActiveJob('job1', true); bpSave();")
            for name in ('iPhone', 'Mac', 'iPad'): await sync(pages[name][0])
            for name in ('iPad', 'Mac'):
                v = await pages[name][0].evaluate("bpActiveJob()")
                ok(v == 'job1', name + ': picks up the job the iPhone is on (' + repr(v) + ')')

            print('\n7. close and reopen every app — nothing lost')
            before = {n: await pages[n][0].evaluate(SNAP) for n in pages}
            for name in pages:
                pg = pages[name][0]
                await pg.reload(); await pg.wait_for_timeout(3500)
                after = await pg.evaluate(SNAP)
                ok(json.dumps(after, sort_keys=True) == json.dumps(before[name], sort_keys=True), name + ': identical after reopening')
                n = await pg.evaluate("(DB.photos||[]).filter(function(p){ return typeof p.src === 'string' && p.src.slice(0,5) === 'data:'; }).length")
                ok(n == 3, name + ': photos still there after reopening (%d)' % n)

            print('\n8. a brand-new device joins and gets everything')
            ctx = await b.new_context(viewport={'width': 1024, 'height': 1366}, has_touch=True)
            await ctx.expose_function('ckCall', ck); await ctx.add_init_script(FAKE_CK)
            pg = await ctx.new_page(); errs['new iPad'] = []; pg.on('pageerror', lambda e: errs['new iPad'].append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(3000)
            await sync(pg)
            s_new = await pg.evaluate(SNAP); s_mac = await pages['Mac'][0].evaluate(SNAP)
            ok(json.dumps(s_new, sort_keys=True) == json.dumps(s_mac, sort_keys=True), 'new iPad matches the Mac exactly after one sync')

            for name in errs:
                ok(not errs[name], name + ': no script errors ' + str(errs[name][:2]))
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)

asyncio.run(main())
