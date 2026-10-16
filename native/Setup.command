#!/bin/bash
# Double-click me. I make the Xcode project and open it.
cd "$(dirname "$0")"
if ! command -v xcodegen >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is not installed. Open https://brew.sh , copy its one-line installer into Terminal, then double-click this file again."
    read -p "Press Return to close"; exit 1
  fi
  brew install xcodegen || { read -p "Install failed. Press Return to close"; exit 1; }
fi
xcodegen && open BuildersPro.xcodeproj
echo "Done. In Xcode: pick your Team under Signing & Capabilities, add iCloud + CloudKit, choose your iPhone, press Play."
read -p "Press Return to close"
