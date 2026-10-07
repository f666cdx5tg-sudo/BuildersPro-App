#!/usr/bin/env python3
"""Snapshot the current index.html into /beta (the testers' copy).
Run ONLY when you want testers to get a new build:  python3 release_beta.py
Testers' data is fully separate from the main app (own database + own settings)."""
import os, re, shutil
src = open('index.html', encoding='utf-8').read()
ver = re.search(r"var APP_VERSION = '([0-9.]+)'", src).group(1)
os.makedirs('beta', exist_ok=True)
iso = """<script>/* BETA copy: private storage so it never touches the main app's data */
(function(){var ls=window.localStorage,P='beta_';var w={getItem:function(k){return ls.getItem(P+k)},setItem:function(k,v){ls.setItem(P+k,v)},removeItem:function(k){ls.removeItem(P+k)},key:function(i){var ks=[];for(var j=0;j<ls.length;j++){var k=ls.key(j);if(k.indexOf(P)===0)ks.push(k.slice(P.length))}return ks[i]===undefined?null:ks[i]},clear:function(){var ks=[];for(var j=0;j<ls.length;j++){var k=ls.key(j);if(k.indexOf(P)===0)ks.push(k)}ks.forEach(function(k){ls.removeItem(k)})}};Object.defineProperty(w,'length',{get:function(){var n=0;for(var j=0;j<ls.length;j++)if(ls.key(j).indexOf(P)===0)n++;return n}});try{Object.defineProperty(window,'localStorage',{value:w,configurable:true})}catch(e){}})();
</script>
<style>body::after{content:"BETA";position:fixed;top:calc(env(safe-area-inset-top) + 2px);right:6px;z-index:2147483647;font:800 10px -apple-system,sans-serif;letter-spacing:.08em;color:#fff;background:#FF9F0A;padding:2px 6px;border-radius:6px;pointer-events:none;opacity:.9}</style>
"""
out = src.replace('<meta charset="UTF-8"/>', '<meta charset="UTF-8"/>\n' + iso, 1)
out = out.replace("indexedDB.open('bp_idb'", "indexedDB.open('bp_idb_beta'")
out = out.replace('href="splash/', 'href="../splash/')
out = out.replace('<title>BuildersPro</title>', '<title>BuildersPro Beta</title>')
out = out.replace("register('sw.js')", "register('sw.js')")  # beta/sw.js (own scope)
assert "bp_idb_beta" in out
open('beta/index.html', 'w', encoding='utf-8').write(out)
open('beta/manifest.webmanifest', 'w').write('{\n  "name": "BuildersPro Beta",\n  "short_name": "BP Beta",\n  "start_url": "./index.html",\n  "scope": "./",\n  "display": "standalone",\n  "background_color": "#f0f5ff",\n  "theme_color": "#f0f5ff"\n}\n')
sw = open('sw.js').read().replace("'bp-app-v1'", "'bp-beta-v1'")
open('beta/sw.js', 'w').write(sw)
print('beta snapshot = v' + ver)
