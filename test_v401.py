"""v4.01: (1) dock/mic never overlap content; (2) auto sync pulls only when the cloud changed, retries pushes; (3) no redraw when nothing changed."""
import json, sys
from playwright.sync_api import sync_playwright
fail=0
def check(name, ok, info=''):
    global fail; print(('PASS ' if ok else 'FAIL ')+name, info); fail += (not ok)
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---- layout: field app
    for vp,z in (((390,844),1),((820,1180),1.3)):
        pg=b.new_page(viewport={'width':vp[0],'height':vp[1]}); pg.goto('http://localhost:8799/index.html'); pg.evaluate("document.getElementById('bp-lock')?.remove()")
        pg.evaluate("DB.jobs=[{id:'j',name:'J',status:'active'}];currentJobId='j';bpSetZoom(%s);showScreen('s-job-detail');renderJobDetail('j')"%z); pg.wait_for_timeout(1200)
        r=pg.evaluate("""(()=>{var sc=document.querySelector('.screen.active').getBoundingClientRect();
          var f=[...document.querySelectorAll('#bp-dock button:not([hidden]),#bp-voice-fab,.fab')].filter(e=>e.offsetParent!==null||getComputedStyle(e).position==='fixed').map(e=>e.getBoundingClientRect()).filter(r=>r.width>0);
          var over=f.filter(r=>r.top<sc.bottom-1);
          var pair=[];for(var i=0;i<f.length;i++)for(var j=i+1;j<f.length;j++){var a=f[i],c=f[j];if(a.left<c.right-1&&c.left<a.right-1&&a.top<c.bottom-1&&c.top<a.bottom-1)pair.push([i,j])}
          return {screenBottom:sc.bottom,vh:innerHeight,n:f.length,over:over.length,pair:pair.length}})()""")
        check('layout %s z=%s: buttons below screen, not overlapping each other'%(vp,z), r['over']==0 and r['pair']==0 and r['n']>=1, r)
        pg.close()
    # ---- sync (field + desktop)
    for u,pull,push in (('index.html','doPull','doPush'),('desktop.html','deskPull','deskPush')):
        pg=b.new_page(viewport={'width':1100,'height':800}); calls={'get':0,'304':0,'write':0}; state={'etag':'W/"a"'}
        def handle(route):
            req=route.request
            if req.method=='GET':
                calls['get']+=1
                if req.headers.get('if-none-match')==state['etag']:
                    calls['304']+=1; route.fulfill(status=304,headers={'ETag':state['etag'],'access-control-allow-origin':'*','access-control-expose-headers':'ETag'}); return
                body={'id':'g1','files':{'bp_data.json':{'content':json.dumps({'db':{'jobs':[]},'blobChunks':[],'pushedAt':'2026-10-09'})}}}
                route.fulfill(status=200,content_type='application/json',headers={'ETag':state['etag'],'access-control-allow-origin':'*','access-control-expose-headers':'ETag'},body=json.dumps(body))
            elif req.method=='OPTIONS':
                route.fulfill(status=204,headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'})
            else:
                calls['write']+=1; route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*','access-control-expose-headers':'ETag'},body=json.dumps({'id':'g1','files':{'bp_data.json':{}}}))
        pg.route('https://api.github.com/**',handle)
        pg.goto('http://localhost:8799/'+u); pg.evaluate("document.getElementById('bp-lock')?.remove()"); pg.wait_for_timeout(500)
        pg.evaluate("_syncToken='tok';_syncGistId='g1'")
        pg.evaluate("window.__renders=0;var o=window.renderAll;if(o)window.renderAll=function(){window.__renders++;return o.apply(this,arguments)};var m=window.mergeIncomingDB;window.__merges=0;window.mergeIncomingDB=function(){window.__merges++;return m.apply(this,arguments)};0")
        pg.evaluate("window.%s()"%pull); pg.wait_for_timeout(1500)
        m1=pg.evaluate("[__merges,__renders,window.__bpGistEtag]")
        pg.evaluate("_lastAutoPullAt=0;maybeAutoPull()"); pg.wait_for_timeout(1200)
        m2=pg.evaluate("[__merges,__renders]")
        check(u+' unchanged cloud -> no merge/redraw (304)', m2[0]==m1[0] and m2[1]==m1[1] and calls['304']>=1, {'m1':m1,'m2':m2,'304':calls['304']})
        state['etag']='W/"b"'
        pg.evaluate("_lastAutoPullAt=0;maybeAutoPull()"); pg.wait_for_timeout(1500)
        m3=pg.evaluate("[__merges,__renders]")
        check(u+' changed cloud -> pulled (merge ran), no redraw if no data change', m3[0]==m2[0]+1 and m3[1]==m2[1], m3)
        # dirty -> auto push
        pg.evaluate("_suppressNextAutoPush=false; (window.saveDB||window.save)()"); pg.wait_for_timeout(3300)
        w0=calls['write']; pg.evaluate("bpAutoSyncTick()"); pg.wait_for_timeout(3500)
        check(u+' unsynced change gets pushed automatically', calls['write']>w0, {'writes':calls['write']-w0})
        pg.close()
    b.close()
sys.exit(1 if fail else 0)
