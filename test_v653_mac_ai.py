"""v6.5.3 — AI on the Mac (Command Center) and in older builds of the app.
1. The current Mac app: key saves, Connected, Test answers.
2. Keychain refuses the key: the reason shows instead of a silent "Not set up".
3. An older build (no AI in it, or one that never answers): says the app is too old, not "Checking…" forever.
Run from repo root: python3 test_v653_mac_ai.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8953
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
def shell(caps, mode):
    return """
window.__key = null;
window.BPShell = { version: 't', caps: %s };
window.webkit = { messageHandlers: { bp: { postMessage: function(m){
  if ('%s' === 'silent') return;
  setTimeout(function(){
    if (m.kind === 'aiKeySet') { if ('%s' === 'refuse') window.bpAIKeyStatus(false, 'Keychain would not save it (code -34018)'); else { window.__key = m.key; window.bpAIKeyStatus(true); } }
    else if (m.kind === 'aiKeyStatus') window.bpAIKeyStatus(!!window.__key);
    else if (m.kind === 'ai') window.bpAIDone(m.id, { ok: true, text: 'ready' });
  }, 20);
} } } };""" % (caps, mode, mode)
async def run(b, file, caps, mode, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    await ctx.add_init_script(shell(caps, mode))
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2200)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
    await pg.evaluate("bpAISettings()"); await pg.wait_for_timeout(300)
    return ctx, pg, errs
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for file, w, h, nm in (('desktop.html', 1440, 900, 'Mac'), ('index.html', 402, 874, 'iPhone')):
                print('\n%s — current app' % nm)
                ctx, pg, errs = await run(b, file, '{ai:true}', 'ok', w, h)
                ok(await pg.is_visible('#bp-ai-settings'), 'AI settings open')
                await pg.fill('#bp-ai-key', 'sk-ant-api03-' + 'x' * 40); await pg.click('#bp-ai-save'); await pg.wait_for_timeout(300)
                t = await pg.inner_text('#bp-ai-settings')
                ok('Connected' in t, 'key saved → Connected')
                await pg.click('#bp-ai-test'); await pg.wait_for_timeout(400)
                ok('Working' in await pg.inner_text('#bp-ai-test-out'), 'Test gets an answer')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

                print('%s — Keychain refuses the key' % nm)
                ctx, pg, errs = await run(b, file, '{ai:true}', 'refuse', w, h)
                await pg.fill('#bp-ai-key', 'sk-ant-api03-' + 'x' * 40); await pg.click('#bp-ai-save'); await pg.wait_for_timeout(300)
                t = await pg.inner_text('#bp-ai-settings')
                ok('Keychain would not save it' in t, 'the reason shows (%s)' % t[:80].replace('\n', ' '))
                await ctx.close()

                print('%s — older build with no AI' % nm)
                ctx, pg, errs = await run(b, file, '{measure:false}', 'ok', w, h)
                ok('too old' in await pg.inner_text('#bp-ai-settings'), 'says the app is too old')
                await ctx.close()

                print('%s — build that never answers' % nm)
                ctx, pg, errs = await run(b, file, '{ai:true}', 'silent', w, h)
                ok('Checking' in await pg.inner_text('#bp-ai-settings') or 'too old' in await pg.inner_text('#bp-ai-settings'), 'starts by checking')
                await pg.wait_for_timeout(4500)
                ok('too old' in await pg.inner_text('#bp-ai-settings'), 'after 4 s says the app is too old (not Checking… forever)')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
