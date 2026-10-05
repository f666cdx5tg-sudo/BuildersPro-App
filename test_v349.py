"""BuildersPro v3.49: header ☰ menus (space actions, photos filter, finance), photo-room dock back, shopping add flow, Room/Area on create."""
import sys, os, subprocess, time, asyncio
REPO = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(REPO, 'test_v347.py'), encoding='utf-8').read().split('REPO = ')[0])
from playwright.async_api import async_playwright
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8797', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx, pg, errs = await make_page(b, zoom=1.15, base='http://localhost:8797/')
            # room ☰
            await pg.evaluate("openRoomDetail('r4')"); await pg.wait_for_timeout(2200)
            ok(await pg.evaluate("document.querySelectorAll('#s-room-detail .detail-header .bp-hm-btn').length===1"), 'room header ☰ missing')
            ok(await pg.evaluate("document.querySelectorAll('#s-room-detail .detail-header .bp-hm-it').length===4"), 'expected 4 menu items')
            await pg.evaluate("document.querySelector('#s-room-detail .bp-hm-btn').click()"); await pg.wait_for_timeout(200)
            ok(await pg.evaluate("document.querySelector('#s-room-detail .bp-hm').classList.contains('open')"), 'menu did not open')
            await pg.screenshot(path='/tmp/v349-room.png')
            await pg.evaluate("bpHMenuClose()")
            # photos ☰ + dock back
            await pg.evaluate("showScreen('s-photos')"); await pg.wait_for_timeout(800)
            ok(await pg.evaluate("document.querySelectorAll('#bp-photo-header .bp-hm-it').length===5"), 'photos ☰ needs 5 items')
            ok(await pg.evaluate("!document.querySelector('#bp-photo-header .bp-kindbar') && !document.querySelector('#bp-photo-header [onclick^=bpSetPhotoSpace]')"), 'old photo filter rows still there')
            await pg.evaluate("bpPhotoFilter('Rooms')"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("window._bpKind==='room'"), 'Rooms filter not applied')
            await pg.evaluate("bpPhotoFilter('All')")
            await pg.evaluate("bpOpenPhotoArea('r1')"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("!document.querySelector('#bp-photo-header').innerText.includes('All Areas')"), 'All Areas button still there')
            ok(await pg.evaluate("!document.getElementById('bp-dock-back').hidden"), 'dock back hidden inside a photo room')
            await pg.evaluate("document.getElementById('bp-dock-back').click()"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("window._bpPhotoArea===null"), 'dock back did not leave the room')
            ok(await pg.evaluate("document.getElementById('bp-dock-back').hidden"), 'dock back should hide on the room list')
            # finance ☰
            await pg.evaluate("showScreen('s-finance')"); await pg.wait_for_timeout(1800)
            ok(await pg.evaluate("document.querySelectorAll('#bp-fin-hm .bp-hm-it').length===8"), 'finance ☰ needs 8 items')
            ok(await pg.evaluate("getComputedStyle(document.getElementById('ftab-grid')).display==='none'"), 'finance tab grid still showing')
            await pg.evaluate("setFinanceTab('permits')"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("document.querySelector('#bp-fin-hm .bp-hm-it.on').innerText.includes('Permits')"), 'finance ☰ does not show current tab')
            bb = await pg.evaluate("(()=>{const r=document.querySelector('#bp-fin-hm .bp-hm-btn').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,innerWidth]})()")
            ok(bb[0] > bb[2]*0.6, f'finance ☰ is not on the right ({bb})')
            await pg.mouse.click(bb[0], bb[1]); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("document.querySelector('#bp-fin-hm .bp-hm').classList.contains('open')"), 'finance ☰ did not open on a real tap')
            ok(await pg.evaluate("(()=>{const r=document.querySelector('#bp-fin-hm .bp-hm-pop').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.width>100})()"), 'finance menu popup is off-screen')
            ok(await pg.evaluate("(()=>{const it=[...document.querySelectorAll('#bp-fin-hm .bp-hm-it')];return it.every(i=>{const r=i.getBoundingClientRect();const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return i.contains(e)})})()"), 'finance menu items are covered by something')
            await pg.screenshot(path='/tmp/v351-fin.png')
            await pg.evaluate("document.querySelectorAll('#bp-fin-hm .bp-hm-it')[2].click()"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("window._financeTab==='expenses'"), 'menu item did not switch tab')
            # job page icon-only
            await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(600)
            ok(await pg.evaluate("document.querySelectorAll('#s-job-detail .bp-act').length===3 && [...document.querySelectorAll('#s-job-detail .bp-act .bp-act-lb')].every(e=>getComputedStyle(e).display==='none')"), 'job page buttons not icon-only')
            ok(await pg.evaluate("document.querySelector('#s-job-detail').innerText.indexOf('Add Area')<0"), 'job page still says Add Area')
            # shopping
            await pg.evaluate("bpOpenShop('')"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("!document.getElementById('bp-shop-text') && !document.body.innerText.includes('Quantity and price are picked out')"), 'old shopping composer/instructions remain')
            ok(await pg.evaluate("getComputedStyle(document.getElementById('bp-shop-add')).backgroundColor==='rgb(48, 209, 88)'"), '+ is not green')
            await pg.evaluate("document.getElementById('bp-shop-add').click()"); await pg.wait_for_timeout(400)
            await pg.evaluate("document.getElementById('bp-sa-qty').value='4';document.getElementById('bp-sa-text').value='PEX elbow';document.getElementById('bp-sa-price').value='2.5'; bpShopSaveNew(false)"); await pg.wait_for_timeout(400)
            ok(await pg.evaluate("DB.shopping.some(x=>x.text==='PEX elbow'&&x.qty===4&&x.price===2.5)"), 'item not saved with qty/name/cost')
            ok(await pg.evaluate("!document.getElementById('bp-shop-new')"), 'add sheet did not close')
            await pg.evaluate("bpShopToggle(DB.shopping.find(x=>x.text==='PEX elbow').id)"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("!!document.getElementById('bp-shop-edit')"), 'checking off did not open edit page')
            await pg.evaluate("document.getElementById('bp-shop-edit').remove()")
            ok(await pg.evaluate("!!document.getElementById('bp-shop-back')"), 'floating back button missing')
            await pg.screenshot(path='/tmp/v349-shop.png')
            await pg.evaluate("bpShopBack()"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("!document.getElementById('bp-shop') && document.body.classList.contains('bp-drawer-open')"), 'back did not reopen slide-over menu')
            # new space kind
            await pg.evaluate("bpDrawerSet(false); openAddRoom()"); await pg.wait_for_timeout(500)
            ok(await pg.evaluate("document.getElementById('ar-kind').value==='room'"), 'ar-kind default')
            ok(not errs, f'JS errors {errs[:2]}')
            await ctx.close(); await b.close()
    finally: srv.terminate()
    print(f'\n{checks-len(fails)}/{checks} checks passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
