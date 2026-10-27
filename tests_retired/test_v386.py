import asyncio, os, base64
from playwright.async_api import async_playwright

BASE = 'http://localhost:8799'
TMP = '/tmp/v386'
os.makedirs(TMP, exist_ok=True)

ok = True
def check(label, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + label + (' ' + str(extra) if extra != '' else ''))
    if not cond: ok = False

async def main():
    # test files: small text, a >512 char "pdf" so it goes through the blob splitter, and an oversized one
    open(TMP + '/note.txt', 'w').write('hello from a note file')
    open(TMP + '/plans.pdf', 'wb').write(b'%PDF-1.4\n' + (b'0123456789abcdef' * 200))
    open(TMP + '/huge.bin', 'wb').write(b'\0' * (16 * 1024 * 1024))

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844})
        page = await ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        for app in ('index.html', 'desktop.html'):
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e, a=app: errs.append(a + ': ' + str(e)))
            await pg.goto(BASE + '/' + app)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            await pg.wait_for_timeout(300)
            v = await pg.evaluate("APP_VERSION")
            check(app + ' version is 3.86', v == '3.86', v)
            icons = await pg.evaluate("""() => ({
              boiler: bpRoomIconHtml('Boiler Room',''), furnace: bpRoomIconHtml('Furnace',''),
              util: bpRoomIconHtml('Utility Room',''), kitchen: bpRoomIconHtml('Kitchen',''),
              yard: bpRoomIconHtml('Front Yard','') })""")
            check(app + ' boiler -> flame', 'data-v386' in icons['boiler'] and 'boiler room' in icons['boiler'])
            check(app + ' furnace -> flame', 'boiler room' in icons['furnace'])
            check(app + ' utility -> wrench room', 'data-v386' in icons['util'] and 'utility room' in icons['util'])
            check(app + ' utility icon differs from boiler', icons['util'] != icons['boiler'])
            check(app + ' kitchen icon untouched', 'data-v311' in icons['kitchen'])
            check(app + ' yard icon untouched', 'data-v380' in icons['yard'])
            await pg.close()

        # ---- field app: notes with files ----
        await page.goto(BASE + '/index.html')
        await page.evaluate("document.getElementById('bp-lock')?.remove()")
        await page.wait_for_timeout(300)
        await page.evaluate("""() => {
          DB.jobs = DB.jobs || []; DB.rooms = DB.rooms || [];
          DB.jobs.push({id:'jobT', name:'Test Job', status:'Active'});
          DB.rooms.push({id:'r1', jobId:'jobT', name:'Boiler Room', type:'Other'}, {id:'r2', jobId:'jobT', name:'Utility Room', type:'Other'});
          window.currentJobId = 'jobT';
        }""")
        await page.evaluate("bpNoteEdit('', 'jobT')")
        await page.wait_for_timeout(300)
        check('editor shows Files button', await page.locator('#bpn-files').count() == 1)
        await page.fill('#bpn-text', 'Boiler inspection notes')
        await page.set_input_files('#bpn-files', [TMP + '/note.txt', TMP + '/plans.pdf', TMP + '/huge.bin'])
        await page.wait_for_timeout(600)
        rows = await page.locator('#bp-notes-ov .nfr').count()
        check('2 files added, oversized one skipped', rows == 2, rows)
        names = await page.locator('#bp-notes-ov .nfr .nfn b').all_inner_texts()
        check('file names listed', names == ['note.txt', 'plans.pdf'], names)
        await page.screenshot(path=TMP + '/editor.png')

        # remove one then re-add to exercise delete
        await page.locator('#bp-notes-ov .nfr button').first.click()
        await page.wait_for_timeout(150)
        check('remove works', await page.locator('#bp-notes-ov .nfr').count() == 1)
        await page.set_input_files('#bpn-files', [TMP + '/note.txt'])
        await page.wait_for_timeout(300)
        check('re-add works', await page.locator('#bp-notes-ov .nfr').count() == 2)

        # open a file -> a blob URL anchor click opens a new page
        async with ctx.expect_page() as newp:
            await page.locator('#bp-notes-ov .nfr .nfn').nth(1).click()
        np = await newp.value
        check('open file spawns a tab with a blob url', np.url.startswith('blob:'), np.url[:30])
        await np.close()

        await page.evaluate("bpNoteSave2()")
        await page.wait_for_timeout(400)
        saved = await page.evaluate("(DB.jobNotes||[]).map(n => ({files:(n.files||[]).map(f => [f.name, f.type, f.size, String(f.src).slice(0,5)])}))")
        check('note saved with 2 files', len(saved) == 1 and len(saved[0]['files']) == 2, saved)

        # list card shows file count
        await page.evaluate("bpOpenNotes('jobT')")
        await page.wait_for_timeout(250)
        card = await page.locator('#bp-notes-ov .nc').first.inner_text()
        check('list card shows the paperclip count', await page.locator('#bp-notes-ov .nc .bp-ic').count() == 1, card)
        await page.screenshot(path=TMP + '/list.png')

        # persistence through the blob store: reload and read it back
        await page.evaluate("bpPersist && new Promise(r => bpPersist(r))")
        await page.wait_for_timeout(500)
        await page.reload()
        await page.evaluate("document.getElementById('bp-lock')?.remove()")
        await page.wait_for_timeout(1200)
        after = await page.evaluate("(DB.jobNotes||[]).map(n => (n.files||[]).map(f => [f.name, String(f.src).slice(0,5), String(f.src).length]))")
        check('files survive reload', len(after) == 1 and len(after[0]) == 2 and all(a[1] == 'data:' for a in after[0]), after)

        # old note without files still edits and saves cleanly
        await page.evaluate("DB.jobNotes.push({id:'old1', jobId:'jobT', roomId:'', text:'old note', created:new Date().toISOString(), updatedAt:new Date().toISOString()})")
        await page.evaluate("bpNoteEdit('old1','jobT')")
        await page.wait_for_timeout(250)
        check('old note opens with no files', await page.locator('#bp-notes-ov .nfr').count() == 0)
        await page.evaluate("bpNoteSave2()")
        await page.wait_for_timeout(250)
        check('old note saved with empty files array', await page.evaluate("Array.isArray(DB.jobNotes.find(n => n.id==='old1').files)"))

        # file-only note (no text) is allowed
        await page.evaluate("bpNoteEdit('', 'jobT')")
        await page.wait_for_timeout(200)
        await page.set_input_files('#bpn-files', [TMP + '/note.txt'])
        await page.wait_for_timeout(300)
        before = await page.evaluate("DB.jobNotes.length")
        await page.evaluate("bpNoteSave2()")
        await page.wait_for_timeout(250)
        check('file-only note saves', await page.evaluate("DB.jobNotes.length") == before + 1)

        # visual: icons on the room list
        await page.evaluate("""() => { var d = document.createElement('div'); d.id='icontest';
          d.style.cssText='position:fixed;top:60px;left:10px;z-index:99999;background:#1c1c1e;color:#0A84FF;padding:14px;font-size:22px;border-radius:12px';
          d.innerHTML = ['Boiler Room','Utility Room','Kitchen','Front Yard'].map(n => bpRoomIconHtml(n,'') + ' ' + n).join('<br>');
          document.body.appendChild(d); }""")
        await page.screenshot(path=TMP + '/icons_in_app.png')

        check('no page errors', len(errs) == 0, errs[:3])
        await browser.close()
    print('\nALL PASS' if ok else '\nSOME FAILED')
    raise SystemExit(0 if ok else 1)

asyncio.run(main())
