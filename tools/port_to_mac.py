#!/usr/bin/env python3
"""Builds the Mac (Command Center) copies of field-app features from index.html, so the two apps
run the SAME feature code. Re-run after changing any of these field modules:

    python3 tools/port_to_mac.py        (rewrites the block between the PORTED markers in desktop.html)

Each port is the field module verbatim, with only the names of the screens/functions swapped for
the Mac's own (its job page, its estimate sheet, its save). Nothing about behavior changes."""
import re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
D_PATH = os.path.join(ROOT, 'desktop.html')
D = open(D_PATH, encoding='utf-8').read()

def module(marker):
    i = F.find(marker)
    if i < 0: sys.exit('marker not found: ' + marker)
    s = F.rfind('<script>', 0, i)
    e = F.find('</script>', i)
    return F[s + len('<script>'):e]

def sub(src, pairs, name):
    for a, b in pairs:
        if a not in src: sys.exit('%s: expected text not found: %r' % (name, a[:80]))
        src = src.replace(a, b)
    return src

ports = []

# ── Security section on every job (v3.77–v3.79) ──
sec = module('v3.77 — SECURITY section on every job')
sec = sub(sec, [
    ("var scr = document.getElementById('s-job-detail'); if (!scr) return;",
     "var scr = document.getElementById('view-job-detail'); if (!scr) return;"),
    ("var anchor = scr.querySelector('.bp-act-row'); if (!anchor) return;",
     "var anchor = document.getElementById('bsp-ready') || document.getElementById('jd2-actions'); if (!anchor) return;"),
    ("s.style.cssText = 'margin:10px 16px 0';", "s.style.cssText = 'margin:12px 0 0;max-width:720px';"),
    ("var orig = renderJobDetail;\nrenderJobDetail = function(jobId){ var r = orig.apply(this, arguments); try { paint(jobId); } catch(e){ console.warn('[BP] v3.77 security', e); } return r; };\nwindow.renderJobDetail = renderJobDetail;",
     "var orig = window.renderDesktopJobDetail;\nwindow.renderDesktopJobDetail = function(jobId){ var r = orig.apply(this, arguments); try { paint(jobId); } catch(e){ console.warn('[BP] security (Mac)', e); } return r; };\ntry { renderDesktopJobDetail = window.renderDesktopJobDetail; } catch(e){}"),
    ("console.log('[BP] v3.77 job Security section ready');", "console.log('[BP Mac] v3.77 job Security section ready (same code as the field app)');"),
], 'security')
sec = re.sub(r'(?<![\w.])save\(\);', 'bpSave();', sec)
ports.append(('Security section (field v3.77)', sec))

# ── BSP phase 1 (v6.1.0) ──
bsp = module('v6.1.0 — BSP, phase 1')
bsp = sub(bsp, [
    ("if (typeof window.saveJob === 'function' && !window.saveJob.__v610) {\n    var _saveJob = window.saveJob;\n    window.saveJob = function(){\n      if (!val('aj-name'))",
     "if (typeof window.saveNewJob === 'function' && !window.saveNewJob.__v610) {\n    var _saveJob = window.saveNewJob;\n    window.saveNewJob = function(){\n      if (!val('nj-name'))"),
    ("var draft = { client: val('aj-client'), address: val('aj-address'), clientEmail: val('aj-client-email'), clientPhone: val('aj-client-phone') };",
     "var draft = { client: val('nj-client'), address: val('nj-address'), clientEmail: val('nj-client-email'), clientPhone: val('nj-client-phone') };"),
    ("    window.saveJob.__v610 = 1;", "    window.saveNewJob.__v610 = 1; try { saveNewJob = window.saveNewJob; } catch(e){}"),
    ("var hdr = document.querySelector('#s-job-detail .detail-header');\n      if (!hdr) return;\n      host = document.createElement('div'); host.id = 'bsp-ready'; host.style.cssText = 'padding:12px 16px 0';",
     "var hdr = document.getElementById('jd2-actions');\n      if (!hdr) return;\n      host = document.createElement('div'); host.id = 'bsp-ready'; host.style.cssText = 'padding:12px 0 0;max-width:720px';"),
    ("if (typeof window.renderJobDetail === 'function' && !window.renderJobDetail.__v610) {\n    var _rjd = window.renderJobDetail;\n    window.renderJobDetail = function(jobId){",
     "if (typeof window.renderDesktopJobDetail === 'function' && !window.renderDesktopJobDetail.__v610) {\n    var _rjd = window.renderDesktopJobDetail;\n    window.renderDesktopJobDetail = function(jobId){"),
    ("    window.renderJobDetail.__v610 = 1;", "    window.renderDesktopJobDetail.__v610 = 1; try { renderDesktopJobDetail = window.renderDesktopJobDetail; } catch(e){}"),
    ("var edit = \"openEditJob('\" + jobId + \"')\";", "var edit = \"editJob('\" + jobId + \"')\";"),
    ("if (typeof window.buildEstimateModal === 'function' && !window.buildEstimateModal.__v610) {\n    var _bem = window.buildEstimateModal;\n    window.buildEstimateModal = function(e){",
     "if (typeof window.buildEstimateModalDesktop === 'function' && !window.buildEstimateModalDesktop.__v610) {\n    var _bem = window.buildEstimateModalDesktop;\n    window.buildEstimateModalDesktop = function(e){"),
    ("    window.buildEstimateModal.__v610 = 1;", "    window.buildEstimateModalDesktop.__v610 = 1; try { buildEstimateModalDesktop = window.buildEstimateModalDesktop; } catch(e){}"),
    ("if (typeof window.saveEstimateModal === 'function' && !window.saveEstimateModal.__v610) {\n    var _sem = window.saveEstimateModal;\n    window.saveEstimateModal = function(){",
     "if (typeof window.saveEstimateModalDesktop === 'function' && !window.saveEstimateModalDesktop.__v610) {\n    var _sem = window.saveEstimateModalDesktop;\n    window.saveEstimateModalDesktop = function(){"),
    ("if (state && !document.getElementById('estimate-modal')) {", "if (state && !document.getElementById('modal-estimate')) {"),
    ("save(); if (typeof renderEstimates === 'function') renderEstimates();", "bpSave(); if (typeof renderDesktopEstimates === 'function') renderDesktopEstimates();"),
    ("    window.saveEstimateModal.__v610 = 1;", "    window.saveEstimateModalDesktop.__v610 = 1; try { saveEstimateModalDesktop = window.saveEstimateModalDesktop; } catch(e){}"),
    ("if (typeof window.emailEstimate === 'function' && !window.emailEstimate.__v610) {\n    var _ee = window.emailEstimate;\n    window.emailEstimate = function(id){",
     "if (typeof window.emailEstimateDesktop === 'function' && !window.emailEstimateDesktop.__v610) {\n    var _ee = window.emailEstimateDesktop;\n    window.emailEstimateDesktop = function(id){"),
    ("    window.emailEstimate.__v610 = 1;", "    window.emailEstimateDesktop.__v610 = 1; try { emailEstimateDesktop = window.emailEstimateDesktop; } catch(e){}"),
    ("if (typeof window.convertEstimateToJob === 'function' && !window.convertEstimateToJob.__v610) {\n    var _conv = window.convertEstimateToJob;\n    window.convertEstimateToJob = function(id){",
     "if (typeof window.convertEstimateToJobDesktop === 'function' && !window.convertEstimateToJobDesktop.__v610) {\n    var _conv = window.convertEstimateToJobDesktop;\n    window.convertEstimateToJobDesktop = function(id){"),
    ("    window.convertEstimateToJob.__v610 = 1;", "    window.convertEstimateToJobDesktop.__v610 = 1; try { convertEstimateToJobDesktop = window.convertEstimateToJobDesktop; } catch(e){}"),
    ("console.log('[BP] v6.1.0 — BSP phase 1: intake gate, contacts, signed contract + CO gates, pick-two pie');",
     "console.log('[BP Mac] v6.1.0 — BSP phase 1 (same code as the field app)');"),
], 'bsp')
bsp = re.sub(r'(?<![\w.])renderJobDetail\(', 'renderDesktopJobDetail(', bsp)
bsp = re.sub(r'(?<![\w.])save\(\);', 'bpSave();', bsp)
bsp = bsp.replace("save(); try { renderDesktopJobDetail(job.id); }", "bpSave(); try { renderDesktopJobDetail(job.id); }")
ports.append(('BSP phase 1 (field v6.1.0)', bsp))

# ── a restore puts clients in the phone book (v6.1.3) ──
rc = module('v6.1.3 — a restore puts clients in the phone book')
rc = re.sub(r'(?<![\w.])save\(\);', 'bpSave();', rc)
ports.append(('Restore adds clients (field v6.1.3)', rc))

# ── Notes with photos, recordings, files (v3.62) ──
nt = module('v3.62 — NOTES: home button, auto title, photos, recordings')
nt = sub(nt, [("if (document.getElementById('modal-new-room')) return;\n", "")], 'notes')
ports.append(('Notes with photos + recordings (field v3.62)', nt))

START, END = '<!-- PORTED FROM FIELD APP: START (tools/port_to_mac.py — do not edit by hand) -->', '<!-- PORTED FROM FIELD APP: END -->'
block = START + '\n' + ''.join('<script>\n/* ═══ PORTED: %s — generated from index.html by tools/port_to_mac.py ═══ */\n%s\n</script>\n' % (n, code.strip('\n')) for n, code in ports) + END
if START in D:
    a = D.index(START); b = D.index(END) + len(END)
    D = D[:a] + block + D[b:]
else:
    D = D.rstrip('\n') + '\n' + block + '\n'   # always the very end: after every other module
open(D_PATH, 'w', encoding='utf-8').write(D)
print('ported', len(ports), 'modules into desktop.html')
