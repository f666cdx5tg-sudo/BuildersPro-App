"""v6.1.18 — photo zoom in the viewer: Command Center (Mac) + field app (iPhone)."""
import subprocess, time, asyncio
from playwright.async_api import async_playwright
SHIM="window.BPShell={version:'t'}; window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
# 400x300 test photo
PHOTO="(function(){var c=document.createElement('canvas');c.width=800;c.height=600;var x=c.getContext('2d');var g=x.createLinearGradient(0,0,800,600);g.addColorStop(0,'#f00');g.addColorStop(1,'#00f');x.fillStyle=g;x.fillRect(0,0,800,600);return c.toDataURL('image/jpeg',.8);})()"
BLOCK=('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')
fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
async def tr(pg):
    return await pg.evaluate("(function(){var i=document.getElementById(window.__id);return i.style.transform})()")
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8821','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            # ── Command Center ──
            ctx=await b.new_context(viewport={'width':1280,'height':820}); await ctx.add_init_script(SHIM)
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:8821/desktop.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); window.__id='dphoto-viewer-img'; DB.jobs=[{id:'j1',name:'Shedwick'}]; DB.photos=[{id:'p1',jobId:'j1',src:"+PHOTO+",date:new Date().toISOString()},{id:'p2',jobId:'j1',src:"+PHOTO+",date:new Date().toISOString()}]; saveDB();")
            await pg.evaluate("viewPhoto('p1')"); await pg.wait_for_timeout(500)
            ok(await pg.is_visible('#bp-pz-ui'),'desk: zoom buttons visible')
            ok(await pg.evaluate("!!document.querySelector('#bp-pz-box #dphoto-viewer-img')"),'desk: image wrapped in clipping frame')
            bb=await pg.locator('#dphoto-viewer-img').bounding_box(); cx,cy=bb['x']+bb['width']*0.3,bb['y']+bb['height']*0.3
            await pg.mouse.move(cx,cy)
            # trackpad pinch = ctrl+wheel
            await pg.keyboard.down('Control'); await pg.mouse.wheel(0,-100); await pg.keyboard.up('Control'); await pg.wait_for_timeout(100)
            t=await tr(pg); ok('scale(' in t,'desk: trackpad pinch zooms ('+t+')')
            pt=await pg.locator('#bp-pz-pct').inner_text(); ok(pt!='100%','desk: % shows '+pt)
            # point under cursor stays put: sample before vs after via math
            ok(await pg.evaluate("window.bpPhotoZoomed()"),'desk: zoomed state')
            # drag pans
            t1=await tr(pg); await pg.mouse.down(); await pg.mouse.move(cx+80,cy+40,steps=4); await pg.mouse.up(); t2=await tr(pg)
            ok(t1!=t2,'desk: drag pans')
            await pg.click('[data-pz="fit"]'); ok((await tr(pg))=='','desk: Fit resets')
            await pg.click('[data-pz="+"]'); ok('scale(1.5)' in await tr(pg),'desk: + button 150%')
            await pg.click('[data-pz="-"]'); ok((await tr(pg))=='','desk: - button back to fit')
            await pg.mouse.dblclick(cx,cy); ok('scale(2.5)' in await tr(pg),'desk: double-click 250%')
            await pg.keyboard.press('0'); ok((await tr(pg))=='','desk: key 0 resets')
            await pg.keyboard.press('='); ok('scale(1.5)' in await tr(pg),'desk: key + zooms')
            # native Mac pinch bridge
            await pg.keyboard.press('0')
            r=await pg.evaluate("bpPhotoPinch(1.4, %f, %f)"%(cx,cy)); ok(r and 'scale(1.4)' in await tr(pg),'desk: native Mac pinch bridge zooms')
            # max/min clamp
            for _ in range(20): await pg.click('[data-pz="+"]')
            ok('scale(8)' in await tr(pg),'desk: capped at 800%')
            # new photo resets
            await pg.evaluate("viewPhoto('p2')"); await pg.wait_for_timeout(150); ok((await tr(pg))=='','desk: next photo opens at fit')
            await pg.click('[data-pz="+"]'); await pg.evaluate("closeModal('modal-photo-viewer')"); await pg.evaluate("viewPhoto('p1')"); await pg.wait_for_timeout(150)
            ok((await tr(pg))=='','desk: reopening starts at fit')
            r=await pg.evaluate("(function(){closeModal('modal-photo-viewer');return bpPhotoPinch(1.5,10,10)})()"); ok(r is False,'desk: pinch ignored when viewer closed')
            await pg.screenshot(path='/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/desk.png')
            ok(not errs,'desk: no page errors '+str(errs[:2]))
            await ctx.close()
            # ── field app (iPhone, touch) ──
            ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); await ctx.add_init_script(SHIM)
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:8821/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove(); window.__id='photo-viewer-img'; DB.jobs=[{id:'j1',name:'Shedwick'}]; DB.photos=[{id:'p1',jobId:'j1',src:"+PHOTO+",date:new Date().toISOString()},{id:'p2',jobId:'j1',src:"+PHOTO+",date:new Date().toISOString()}]; save();")
            await pg.evaluate("viewPhoto('p1','gallery')"); await pg.wait_for_timeout(500)
            ok(await pg.is_visible('#bp-pz-ui'),'field: zoom buttons visible')
            cnt0=await pg.evaluate("document.getElementById('viewer-count').textContent")
            # pinch via CDP touch events
            cdp=await ctx.new_cdp_session(pg)
            bb=await pg.locator('#photo-viewer-img').bounding_box(); mx,my=bb['x']+bb['width']/2,bb['y']+bb['height']/2
            async def touch(t,pts): await cdp.send('Input.dispatchTouchEvent',{'type':t,'touchPoints':[{'x':x,'y':y,'id':i} for i,(x,y) in enumerate(pts)]})
            await touch('touchStart',[(mx-30,my),(mx+30,my)])
            for d in range(30,121,15): await touch('touchMove',[(mx-d,my),(mx+d,my)])
            await touch('touchEnd',[])
            await pg.wait_for_timeout(100)
            t=await tr(pg); ok('scale(' in t,'field: pinch zooms ('+t+')')
            # one-finger drag pans and does NOT change photo
            t1=t; await touch('touchStart',[(mx,my)]); 
            for d in range(0,200,25): await touch('touchMove',[(mx-d,my)])
            await touch('touchEnd',[]); await pg.wait_for_timeout(100)
            cnt1=await pg.evaluate("document.getElementById('viewer-count').textContent")
            ok((await tr(pg))!=t1,'field: drag pans while zoomed')
            ok(cnt1==cnt0,'field: swipe does not change photo while zoomed ('+cnt0+' → '+cnt1+')')
            await pg.click('[data-pz="fit"]'); ok((await tr(pg))=='','field: Fit resets')
            # swipe at fit still changes photo
            await touch('touchStart',[(mx-100,my)])
            for d in range(0,200,25): await touch('touchMove',[(mx-100+d,my)])
            await touch('touchEnd',[]); await pg.wait_for_timeout(200)
            cnt2=await pg.evaluate("document.getElementById('viewer-count').textContent")
            ok(cnt2!=cnt0,'field: swipe at fit still moves to next photo ('+cnt2+')')
            await pg.screenshot(path='/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/field.png')
            ok(not errs,'field: no page errors '+str(errs[:2]))
            await b.close()
    finally: srv.terminate()
    print('\n%d failures'%len(fails))
asyncio.run(main())
