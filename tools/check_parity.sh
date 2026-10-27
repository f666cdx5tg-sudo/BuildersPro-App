#!/bin/bash
# The Mac's copies of field-app features must be rebuilt from the current field app.
# Fails if someone changed a ported field module without re-running tools/port_to_mac.py.
cd "$(dirname "$0")/.."
cp desktop.html /tmp/_desk_before.html
python3 tools/port_to_mac.py > /dev/null || { echo "PORT FAILED — a ported field module changed shape; update tools/port_to_mac.py"; exit 1; }
if ! cmp -s desktop.html /tmp/_desk_before.html; then
  cp /tmp/_desk_before.html desktop.html
  echo "MAC OUT OF STEP — run: python3 tools/port_to_mac.py  (then commit desktop.html)"; exit 1
fi
echo "Mac copies of field features are current"
