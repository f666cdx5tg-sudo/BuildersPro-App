#!/bin/bash
# Runs every active test (test_*.py in the repo root) — several at a time, each on its own port,
# in a scratch copy so nothing in the repo is touched. Prints one line per test and a total.
# Usage: bash tools/run_all_tests.sh [parallel=4]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; P="${1:-4}"
WORK="$(mktemp -d)"; cp -r "$ROOT"/. "$WORK"/; rm -rf "$WORK/.git"; cd "$WORK"
python3 tools/make_test_fixtures.py >/dev/null
python3 - <<'PY'
import re, glob
for i, f in enumerate(sorted(glob.glob('test_*.py'))):
    s = open(f).read(); new = str(9500 + i)
    ports = set(re.findall(r"http\.server['\"],\s*['\"](\d{4})['\"]", s)) | set(re.findall(r"localhost:(\d{4})", s)) | set(re.findall(r"PORT\s*=\s*(\d{4})", s))
    for p in ports:
        s = re.sub(r"(http\.server['\"],\s*['\"])" + p + r"(['\"])", r"\g<1>" + new + r"\g<2>", s)
        s = s.replace('localhost:' + p, 'localhost:' + new); s = re.sub(r"(PORT\s*=\s*)" + p, r"\g<1>" + new, s)
    if ports and not re.search(r"http\.server", s):   # tests that expect a server already running
        s = ("import subprocess as _sp, time as _t, os as _os, atexit as _ae\n_srv=_sp.Popen(['python3','-m','http.server','" + new +
             "','--directory',_os.path.dirname(_os.path.abspath(__file__))],stdout=_sp.DEVNULL,stderr=_sp.DEVNULL); _t.sleep(1); _ae.register(_srv.terminate)\n" + s)
    open(f, 'w').write(s)
PY
mkdir -p logs; : > logs/summary.txt
ls test_*.py | sort -V | xargs -P "$P" -I{} bash -c 'timeout 600 python3 {} > logs/{}.log 2>&1; echo "$? {}" >> logs/summary.txt'
pass=$(awk '$1==0' logs/summary.txt | wc -l); total=$(wc -l < logs/summary.txt)
while read rc t; do if grep -q '^SKIPPED' logs/$t.log; then echo "SKIP $t"; elif [ "$rc" = 0 ]; then echo "PASS $t"; else echo "FAIL $t"; fi; done < logs/summary.txt | sort -k2 -V
echo "$pass of $total tests pass   (logs: $WORK/logs)"
[ "$pass" -eq "$total" ]
