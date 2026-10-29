"""v6.4.0 — AI assistant (simulated AI; the real calls go through the App Store app).
1. Settings: key saved through the app, never kept by the page; status shows.
2. Spending: Ask AI marks the expenses it says are money counted again.
3. Spelling: a misspelled text box gets a Fix chip; Full Day PDF / EOD / change order go through a spelling review first.
4. Smart checklist: builds from trades + photos + town + notes, adds only what you tick, skips what's already there.
Run from repo root: python3 test_v640_ai.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, json
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8940
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SHELL = r"""
window.__ai = []; window.__key = null; window.__posts = [];
window.BPShell = { version: 't', caps: { ai: true } };
window.webkit = { messageHandlers: { bp: { postMessage: function(m){
  window.__posts.push(m.kind);
  setTimeout(function(){
    if (m.kind === 'aiKeySet') { window.__key = m.key; window.bpAIKeyStatus(true); }
    else if (m.kind === 'aiKeyStatus') window.bpAIKeyStatus(!!window.__key);
    else if (m.kind === 'aiKeyClear') { window.__key = null; window.bpAIKeyStatus(false); }
    else if (m.kind === 'ai') {
      window.__ai.push(m.body);
      var c = m.body.messages[0].content, txt = typeof c === 'string' ? c : c.filter(function(x){ return x.type === 'text'; }).map(function(x){ return x.text; }).join('');
      var imgs = typeof c === 'string' ? 0 : c.filter(function(x){ return x.type === 'image'; }).length;
      window.__lastImgs = imgs;
      var out;
      if (/ready/.test(txt) && txt.length < 60) out = 'ready';
      else if (/^Records:/.test(txt)) out = JSON.stringify({ repeats: [{ keep: 'e1', extra: ['e2'], why: 'Receipt scan and shopping list entry for the same Home Depot run', sure: 'high' }], subDoubles: [{ id: 'e5', why: 'Pays Rivera, already counted in full' }], summary: 'Two entries look like money counted again.' });
      else if (/^Text: /.test(txt)) out = JSON.stringify({ fixed: JSON.parse(txt.slice(6, txt.indexOf('\n'))).replace('recieved', 'received').replace('Instal ', 'Install ') });
      else if (/^Lines:/.test(txt)) { var L = JSON.parse(txt.slice(7, txt.indexOf('\nReturn'))); out = JSON.stringify({ fixes: L.filter(function(l){ return /recieved|instal |fauset/i.test(l.t); }).map(function(l){ return { n: l.n, fixed: l.t.replace('recieved','received').replace(/instal /i, function(m){ return m[0] + 'nstall '; }).replace('fauset','faucet') }; }) }); }
      else if (/Build the work checklist/.test(txt)) out = 'Here: ' + JSON.stringify({ items: [{ text: 'Set toilet flange', trade: 'Plumbing', code: '', why: '' }, { text: 'Rough-in shower valve at 48"', trade: 'Plumbing', code: 'IPC 424.3', why: '' }, { text: 'Install GFCI at vanity', trade: 'Electrical', code: 'NEC 210.8', why: 'Photo shows no GFCI' }] });
      else out = '{}';
      window.bpAIDone(m.id, { ok: true, text: out });
    }
  }, 20);
} } } };
"""
PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
SEED = """(png) => { var t = new Date().toISOString(), d = t.slice(0,10);
  DB.jobs=[{id:'j1',name:'N. Peach St',address:'1536 N. Peach St',city:'Philadelphia',state:'PA',zip:'19131',status:'Active',contract:20000,updatedAt:t}];
  DB.rooms=[{id:'r1',jobId:'j1',name:'(F) Bathroom',type:'Bathroom',level:'Level 1',notes:'Client wants niche',updatedAt:t}];
  DB.punchlist=[{id:'p1',jobId:'j1',roomId:'r1',text:'Set toilet flange',trade:'Plumbing',done:false,created:t,updatedAt:t},{id:'p2',jobId:'j1',roomId:'r1',text:'Instal fauset',trade:'Plumbing',done:true,created:t,updatedAt:t}];
  DB.photos=[{id:'ph1',jobId:'j1',roomId:'r1',src:png,date:t,created:t}];
  DB.contractors=[{id:'c1',jobId:'j1',name:'Mike Rivera',value:6000}];
  DB.expenses=[{id:'e1',jobId:'j1',desc:'Materials — Home Depot',vendor:'Home Depot',amount:412.37,date:d,category:'Materials'},
               {id:'e2',jobId:'j1',desc:'HD run',vendor:'Home Depot',amount:409.10,date:d,category:'Materials'},
               {id:'e5',jobId:'j1',desc:'Draw',vendor:'',amount:2500,date:d,category:'Labor'}];
  DB.reports=[{id:'rp1',jobId:'j1',date:d,notes:'Material recieved, all good',workers:'2'}];
  DB.changeOrders=[{id:'co1',jobId:'j1',title:'Add niche',description:'Instal niche in shower',amount:450,status:'Draft'}];
  try{bpSave()}catch(e){try{saveDB()}catch(e2){}} try{bpSetActiveJob('j1',true)}catch(e){} }"""
async def field(b):
    print('\niPhone (in the app)')
    ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True)
    await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined;")
    await pg.evaluate(SEED, PNG)
    ok(await pg.evaluate("APP_VERSION") >= '6.4.0', 'on v6.4.0')
    ok(await pg.evaluate("!!document.getElementById('nav-ai') && !!document.querySelector('#nav-ai svg')"), 'AI assistant is in the side menu with a line icon')
    # settings
    await pg.evaluate("bpAISettings()"); await pg.wait_for_timeout(300)
    ok('Not set up yet' in await pg.inner_text('#bp-ai-settings'), 'settings: not set up yet')
    await pg.fill('#bp-ai-key', 'sk-ant-test-key-1234567890abcdef'); await pg.click('#bp-ai-save'); await pg.wait_for_timeout(300)
    ok('Connected' in await pg.inner_text('#bp-ai-settings'), 'saving the key: Connected')
    ok(await pg.evaluate("JSON.stringify(localStorage).indexOf('sk-ant-test') < 0 && JSON.stringify(DB).indexOf('sk-ant-test') < 0"), 'the key is never kept by the page (only the app Keychain)')
    await pg.click('#bp-ai-test'); await pg.wait_for_timeout(300)
    ok('Working' in await pg.inner_text('#bp-ai-test-out'), 'Test: the AI answered')
    await pg.evaluate("document.getElementById('bp-ai-settings').remove()")
    # spending
    await pg.evaluate("bpMoneyCheck('j1')"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("!!document.getElementById('bp-mcheck-ask')"), 'Money check has Ask AI')
    await pg.click('#bp-mcheck-ask'); await pg.wait_for_timeout(500)
    t = await pg.inner_text('#bp-mcheck')
    ok('2 expenses look like money counted again' in t, 'AI marks 2 expenses as counted again')
    ok(await pg.evaluate("!!document.querySelector('#bp-mcheck [onclick*=\"e2\"] [data-ai-mark]') && !!document.querySelector('#bp-mcheck [onclick*=\"e5\"] [data-ai-mark]') && !document.querySelector('#bp-mcheck [onclick*=\"e1\"] [data-ai-mark]')"), 'the extra copy and the sub payment are marked; the one to keep is not')
    body = await pg.evaluate("__ai[__ai.length-1]")
    ok(body['model'] == 'claude-sonnet-5-5' and body['max_tokens'] >= 8000 and 'e1' in json.dumps(body), 'spending check sends every expense to the bigger model with room for a full answer')
    ok(await pg.evaluate("!!document.getElementById('bp-mcheck-fix')"), 'a Remove-the-extras button appears')
    await pg.click('#bp-mcheck-fix'); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#bp-mfix [data-mx]').length") == 2, 'the remove sheet lists the 2 extras with checkboxes')
    await pg.evaluate("document.querySelectorAll('#bp-mfix [data-mx]')[1].click()"); await pg.wait_for_timeout(100)
    ok('Remove 1' in await pg.inner_text('#bp-mfix-go'), 'untick one: Remove 1')
    await pg.click('#bp-mfix-go'); await pg.wait_for_timeout(400)
    ids = await pg.evaluate("DB.expenses.map(function(e){ return e.id; })")
    ok('e2' not in ids and 'e5' in ids and 'e1' in ids, 'only the ticked extra is removed (%s)' % ids)
    ok(await pg.evaluate("JSON.stringify(DB.recycle || DB.recycleBin || DB._recycle || {}).indexOf('e2') >= 0 || JSON.stringify(localStorage).indexOf('e2') >= 0"), 'the removed expense is in the Recycle Bin')
    await pg.evaluate("bpMoneyCheckClose()")
    # spelling on save
    await pg.evaluate("var i=document.createElement('input'); i.id='bp-note-x'; i.type='text'; document.getElementById('s-home').appendChild(i); i.value='Material recieved'; i.dispatchEvent(new Event('change',{bubbles:true}));")
    await pg.wait_for_timeout(400)
    ok(await pg.evaluate("!!document.querySelector('#bp-note-x + .bp-sp-chip')"), 'a misspelled text box gets a Spelling chip')
    await pg.click('#bp-note-x + .bp-sp-chip [data-fix]')
    ok(await pg.evaluate("document.getElementById('bp-note-x').value") == 'Material received', 'Fix corrects it')
    await pg.evaluate("var p=document.createElement('input'); p.id='bp-price-x'; p.type='text'; p.placeholder='Price'; document.body.appendChild(p); p.value='recieved 12'; p.dispatchEvent(new Event('change',{bubbles:true}));"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("!document.querySelector('#bp-price-x + .bp-sp-chip')"), 'number / price boxes are not spell-checked')
    # before sending
    await pg.evaluate("window.__sent=''; window.bpOpenPhotoReport=function(id){ window.__sent='report:'+id; }; bpSendPick('report','rp1')"); await pg.wait_for_timeout(500)
    rv = await pg.inner_text('#bp-spell-review') if await pg.evaluate("!!document.getElementById('bp-spell-review')") else ''
    ok('2 spelling fixes' in rv and 'received' in rv and 'install faucet' in rv.lower(), 'Full Day PDF: spelling review lists the fixes first (%s)' % rv[:60].replace('\n',' '))
    await pg.click('#bp-sr-fix'); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("window.__sent") == 'report:rp1', 'Fix and send: the PDF goes out')
    ok(await pg.evaluate("DB.reports[0].notes") == 'Material received, all good' and (await pg.evaluate("DB.punchlist[1].text")).lower() == 'install faucet', 'the fixes are saved on the report and the checklist item')
    await pg.evaluate("window.__co=''; var o=window.emailChangeOrder; window.emailChangeOrder; "); 
    # change order
    co = await pg.evaluate("(function(){ return typeof emailChangeOrder; })()")
    if co == 'function':
        await pg.evaluate("window.__mailed=0; var real=window.open; window.open=function(){ window.__mailed++; }; location.__hrefSet=0;")
        await pg.evaluate("emailChangeOrder('co1')"); await pg.wait_for_timeout(500)
        ok(await pg.evaluate("!!document.getElementById('bp-spell-review')") and 'niche' in (await pg.inner_text('#bp-spell-review')).lower(), 'change order: spelling review before it goes out')
        await pg.evaluate("document.getElementById('bp-spell-review') && document.getElementById('bp-spell-review').remove()")
    # smart checklist
    await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(700)
    ok(await pg.evaluate("!!document.querySelector('#s-room-detail .bp-act-row [data-ai-list] svg')"), 'each space has a Smart list button (line icon)')
    await pg.click('#s-room-detail [data-ai-list]'); await pg.wait_for_timeout(300)
    t = await pg.inner_text('#bp-ai-list')
    ok('Philadelphia' in t and 'photo' in t and 'notes' in t, 'it says what it will use: photos, town, notes')
    await pg.click('#bp-al-go'); await pg.wait_for_timeout(800)
    body = await pg.evaluate("__ai[__ai.length-1]")
    ok(body['model'] == 'claude-sonnet-5-5' and await pg.evaluate("window.__lastImgs") == 1, 'checklist uses the bigger model and sends the room photo')
    sent = json.dumps(body)
    ok('Philadelphia' in sent and 'niche' in sent and 'Set toilet flange' in sent, 'sends the town, notes and what is already on the list')
    rows = await pg.evaluate("document.querySelectorAll('#bp-al-out [data-ai]').length")
    ok(rows == 2, 'skips what is already on the list (2 new of 3)')
    await pg.evaluate("document.querySelectorAll('#bp-al-out [data-ai]')[1].click()"); await pg.wait_for_timeout(100)
    ok('Add 1' in await pg.inner_text('#bp-al-add'), 'untick one: Add 1')
    n0 = await pg.evaluate("DB.punchlist.length"); await pg.click('#bp-al-add'); await pg.wait_for_timeout(500)
    added = await pg.evaluate("DB.punchlist.slice(%d)" % n0)
    ok(len(added) == 1 and added[0]['roomId'] == 'r1' and added[0]['trade'] == 'Plumbing' and 'IPC' in added[0]['extraNotes'], 'adds only the ticked item, in this space, with its code note')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def browser_and_mac(b):
    print('\nPlain browser')
    ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); bpAISettings()"); await pg.wait_for_timeout(200)
    ok('Works in the BuildersPro app' in await pg.inner_text('#bp-ai-settings'), 'outside the app it says AI works in the BuildersPro app')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
    print('\nCommand Center (in the app)')
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await ctx.add_init_script(SHELL + "window.__key='saved-in-keychain';")
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined;")
    await pg.evaluate(SEED, PNG); await pg.evaluate("window.__key='k'")
    ok(await pg.evaluate("APP_VERSION") >= '6.4.0', 'Command Center is v6.4.0')
    ok(await pg.evaluate("!!document.getElementById('ni-ai')"), 'AI assistant in the Mac sidebar')
    await pg.evaluate("bpMoneyCheck('j1')"); await pg.wait_for_timeout(200); await pg.click('#bp-mcheck-ask'); await pg.wait_for_timeout(500)
    ok('look like money counted again' in await pg.inner_text('#bp-mcheck'), 'Mac: Ask AI spending check works')
    await pg.evaluate("bpMoneyCheckClose(); openRoomDetail('r1')"); await pg.wait_for_timeout(600)
    ok(await pg.evaluate("!!document.querySelector('#modal-room-detail [data-ai-list]')"), 'Mac: Smart checklist button in the space window')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await field(b); await browser_and_mac(b); await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
