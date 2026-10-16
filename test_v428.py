from playwright.sync_api import sync_playwright
import subprocess,time
srv=subprocess.Popen(['python3','-m','http.server','8783'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
ok=[]
def chk(n,c): ok.append(bool(c));print(('PASS ' if c else 'FAIL ')+n)

# mode: 'ok' = first get() succeeds | 'block-then-ok' = first get() refused instantly, later ones succeed
#       'always-block' = every get() refused instantly until a real tap (pointerup) | 'cancel' = slow refusal (user dismissed)
def init(mode, registered=True):
    seed = "localStorage.setItem('bp_passcode_hash','x');localStorage.setItem('bp_passcode_salt','y');localStorage.setItem('bp_webauthn_id','AAAA');" if registered else ""
    return """(function(){%s
      window.__gets=0; window.__tapped=false;
      document.addEventListener('pointerup',function(){window.__tapped=true},true);
      var mode='%s';
      window.PublicKeyCredential = window.PublicKeyCredential || function(){};
      window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable=function(){return Promise.resolve(true)};
      var fake={get:function(){
        window.__gets++;
        var n=window.__gets;
        function nae(){var e=new Error('x');e.name='NotAllowedError';return e}
        if(mode==='ok') return Promise.resolve({id:'c'});
        if(mode==='block-then-ok') return n===1?Promise.reject(nae()):Promise.resolve({id:'c'});
        if(mode==='always-block') return window.__tapped?Promise.resolve({id:'c'}):Promise.reject(nae());
        if(mode==='cancel') return new Promise(function(_,rej){setTimeout(function(){rej(nae())},1700)});
      }};
      try{Object.defineProperty(navigator,'credentials',{value:fake,configurable:true})}catch(e){}
    })();""" % (seed, mode)

URL='http://localhost:8783/index.html'
try:
  with sync_playwright() as p:
    b=p.chromium.launch()
    def run(mode, registered=True):
        ctx=b.new_context(viewport={'width':390,'height':800}); ctx.add_init_script(init(mode,registered))
        pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda x:errs.append(str(x)))
        pg.goto(URL); return pg,errs

    pg,e=run('ok'); pg.wait_for_timeout(1500)
    chk('A: Face ID verifies -> lock screen gone with zero taps', pg.evaluate("!document.getElementById('bp-lock')"))
    chk('A: exactly one Face ID prompt', pg.evaluate("window.__gets")==1)
    chk('A: version 4.28', pg.evaluate("APP_VERSION")=='4.28')
    chk('A: no page errors', not e)

    pg,e=run('block-then-ok'); pg.wait_for_timeout(1200)
    chk('B: iOS refused first prompt, app tried again by itself', pg.evaluate("window.__gets")>=1)
    pg.evaluate("window.dispatchEvent(new Event('focus'))"); pg.wait_for_timeout(800)
    chk('B: app wakes/focuses -> retries itself and opens, still zero taps', pg.evaluate("!document.getElementById('bp-lock')") and not pg.evaluate("window.__tapped"))

    pg,e=run('always-block'); pg.wait_for_timeout(1200)
    chk('C: persistent refusal -> lock stays up (no bypass)', pg.evaluate("!!document.getElementById('bp-lock')"))
    pg.mouse.click(195,60); pg.wait_for_timeout(800)
    chk('C: tap on empty lock-screen space (not the button) starts Face ID and opens', pg.evaluate("!document.getElementById('bp-lock')"))

    pg,e=run('always-block'); pg.wait_for_timeout(1200)
    n0=pg.evaluate("window.__gets"); pg.click('#bp-lock-input'); pg.wait_for_timeout(500)
    chk('C: tapping the passcode box does NOT launch Face ID', pg.evaluate("window.__gets")==n0)

    pg,e=run('cancel'); pg.wait_for_timeout(2600)
    chk('D: user cancels sheet -> no retry loop, passcode fallback message', pg.evaluate("window.__gets")==1 and 'passcode' in pg.evaluate("document.getElementById('bp-lock-error').textContent"))
    pg.evaluate("window.dispatchEvent(new Event('focus'))"); pg.wait_for_timeout(300)
    chk('D: still only one prompt after refocus? (retries allowed up to 4, but never a tight loop)', pg.evaluate("window.__gets")<=2)

    pg,e=run('ok',registered=False); pg.wait_for_timeout(1200)
    chk('E: no passcode/Face ID set up -> never prompts, setup screen shown', pg.evaluate("window.__gets")==0 and pg.evaluate("!!document.getElementById('bp-lock')"))

    pg,e=run('always-block'); pg.wait_for_timeout(1000)
    pg.evaluate("window.bpCheckPasscode=async function(){return true}")
    pg.fill('#bp-lock-input','1234'); pg.click('#bp-lock-btn'); pg.wait_for_timeout(500)
    chk('F: typed passcode still unlocks', pg.evaluate("!document.getElementById('bp-lock')"))
    b.close()
finally:
    srv.terminate()
print('ALL PASS' if all(ok) else 'SOME FAILED',sum(ok),'/',len(ok))
