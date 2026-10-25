# BuildersPro (native) — setup, step by step

This is the starter ("scaffold") for the real iPhone / iPad / Mac app. It already has:
Jobs → Spaces (grouped by level, press-and-hold to drag between levels) → Punch lists and Photos,
progress "20/22 · 2 left", and iCloud sync built in. Your web app (index.html) is untouched.

## Fastest way: double-click **Setup.command** in this folder (it does steps 1–3 for you), then continue at step 4.

## One-time setup (about 10 minutes, on your Mac)
1. Open **Terminal** (Spotlight → type Terminal).
2. Install the project maker (one line): `brew install xcodegen`
   (No Homebrew? Go to brew.sh and paste its one-line installer first.)
3. In Terminal: `cd` into this `native` folder, then run: `xcodegen`
   It creates **BuildersPro.xcodeproj**. Double-click it to open in Xcode.
4. In Xcode: click **BuildersPro** (top of the left list) → **Signing & Capabilities**
   → pick your Apple Developer **Team**.
5. Same screen → **iCloud** → tick **CloudKit** → under Containers press **+** and add
   `iCloud.com.stanrobinson.builderspro` (change the name everywhere if you prefer another).
6. Pick your iPhone (or "My Mac") at the top → press **Play ▶**.

If Xcode complains the bundle ID is taken, change `com.stanrobinson` in `project.yml`
(both places) and in `Config/BuildersPro.entitlements`, then run `xcodegen` again.

## Before you ship to the App Store
In CloudKit Dashboard (icloud.developer.apple.com), press **Deploy Schema to Production**.

## What is NOT built yet (next phases)
Money/expenses, daily report + PDF, markup on photos, importing your data from the web app,
Command Center layout for Mac, widgets. Nothing here was compiled by me — I can't run Xcode —
so expect to send me any red errors Xcode shows and I'll fix them.


## Putting it on your iPhone
Plug the iPhone into the Mac (or use Wi-Fi pairing), unlock it, choose it at the top of Xcode, press Play.
First time only: on the iPhone go to Settings → Privacy & Security → turn on **Developer Mode**, and trust your developer certificate (Settings → General → VPN & Device Management).
