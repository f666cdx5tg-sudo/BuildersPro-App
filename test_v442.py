"""BuildersPro v4.42 (checking off an item no longer re-hashes every photo: tap cost no longer grows with the photo count).
Run from repo root: python3 test_v442.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{
 var big=function(i){return 'data:image/jpeg;base64,'+String.fromCharCode(65+(i%26)).repeat(300000)+i;};
 DB.jobs.push({id:'tj',name:'N. Peach St',status:'Active'});
 ['Bath','Bedroom','Kitchen'].forEach((n,i)=>DB.rooms.push({id:'r'+i,jobId:'tj',name:n,type:'Other'}));
 for(var i=0;i<60;i++) DB.punchlist.push({id:'p'+i,jobId:'tj',roomId:'r'+(i%3),text:'Item '+i,title:'x',trade:'Plumbing',done:i%2===0,created:'2026-10-01',photosBefore:i<20?[{src:big(i),date:'2026-10-01'}]:[]});
 for(var i=0;i<40;i++) DB.photos.push({id:'ph'+i,jobId:'tj',roomId:'r'+(i%3),src:big(100+i),date:'2026-10-05'});
 window._bpPunchJob='tj'; showScreen('s-punch'); bpOpenPunchArea('r0');
})()"""
FNV = "(s=>{var h=0x811c9dc5;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=(h*0x01000193)>>>0}return h.toString(36)+'_'+s.length.toString(36)})"
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8789/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.46'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED); await pg.wait_for_timeout(800)
        # 1) caching: a second full split is far cheaper than the first, and produces identical refs
        r = await pg.evaluate("""(()=>{
          bpWarmBlobHashes.__noop=1; _bhCache=new Map();
          var b1={},t0=performance.now(); var m1=bpSplitBlobs(DB,b1); var d1=performance.now()-t0;
          var b2={},t1=performance.now(); var m2=bpSplitBlobs(DB,b2); var d2=performance.now()-t1;
          return {d1:d1,d2:d2,same:JSON.stringify(Object.keys(b1).sort())===JSON.stringify(Object.keys(b2).sort())&&JSON.stringify(m1)===JSON.stringify(m2),n:Object.keys(b1).length}})()""")
        ok(r['n']==60, f'{t}: seeded blobs {r["n"]}')
        ok(r['same'], f'{t}: refs/meta must be identical with and without the cache')
        ok(r['d2'] < r['d1'] / 3 and r['d2'] < 150, f'{t}: cached split not faster (cold {r["d1"]:.0f}ms, warm {r["d2"]:.0f}ms)')
        # 2) hash values are still the original FNV-1a, so refs already stored/synced keep matching
        ok(await pg.evaluate("(()=>{var f=%s;var s=DB.photos[3].src;return bpBlobHash(s)===f(s)})()" % FNV), f'{t}: hash must equal plain FNV-1a')
        # 3) cache holds only live photos: delete some, split again, deleted ones are gone from memory
        n0 = await pg.evaluate("_bhCache.size")
        await pg.evaluate("DB.photos.splice(0,25);bpSplitBlobs(DB,{})")
        n1 = await pg.evaluate("_bhCache.size")
        ok(n0 - n1 == 25, f'{t}: deleted photos should leave the cache ({n0} -> {n1})')
        # 4) background pre-warm fills the cache without a full save
        await pg.evaluate("_bhCache=new Map()")
        await pg.evaluate("bpWarmBlobHashes()"); await pg.wait_for_timeout(3500)
        live = await pg.evaluate("(()=>{var b={};bpSplitBlobs(DB,b);return Object.keys(b).length})()")
        ok(live == 35, f'{t}: live blobs {live}')
        await pg.evaluate("_bhCache=new Map();bpWarmBlobHashes()"); await pg.wait_for_timeout(3500)
        ok(await pg.evaluate("_bhCache.size")>=live, f'{t}: pre-warm should have cached every live photo ({await pg.evaluate("_bhCache.size")} of {live})')
        # 5) a tick: instant handler, saves, survives a reload
        await pg.evaluate("window._bpPunchJob='tj';showScreen('s-punch');bpOpenPunchArea('r0')"); await pg.wait_for_timeout(500)
        before = await pg.evaluate("DB.punchlist.find(x=>x.id==='p3').done")
        ms = await pg.evaluate("(()=>{var t=performance.now();togglePunchItem('p3');return performance.now()-t})()")
        ok(ms < 150, f'{t}: tick handler took {ms:.0f}ms')
        ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p3').done")!=before, f'{t}: item did not toggle')
        await pg.wait_for_timeout(1500)
        await pg.reload(); await pg.wait_for_timeout(3000)
        ok(await pg.evaluate("DB.punchlist.find(x=>x.id==='p3').done")!=before, f'{t}: tick lost after reload')
        ok(await pg.evaluate("DB.punchlist.filter(x=>x.photosBefore&&x.photosBefore.length&&x.photosBefore[0].src.startsWith('data:image')).length")==20, f'{t}: photos intact after reload')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8789','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
