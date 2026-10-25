#!/bin/bash
# One version number for every BuildersPro app: iPhone/iPad web app, Mac Command Center, native App Store app.
w=$(grep -o "^var APP_VERSION = '[^']*'" index.html | cut -d"'" -f2)
d=$(grep -o "^var APP_VERSION = '[^']*'" desktop.html | cut -d"'" -f2)
n=$(grep -o 'MARKETING_VERSION: "[^"]*"' native/project.yml | cut -d'"' -f2)
echo "field app $w | command center $d | native app $n"
[ "$w" = "$d" ] && [ "$w" = "$n" ] || { echo "VERSION MISMATCH"; exit 1; }
