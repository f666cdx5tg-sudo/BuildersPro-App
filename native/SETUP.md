# BuildersPro native app (v6) — a frame around the live web app

Since v6.0.0 the native app shows the **live web app** from GitHub Pages inside a real
iPhone / iPad / Mac app. Every web fix pushed to GitHub appears on the next launch —
no Xcode rebuild. You only rebuild in Xcode when this `native` folder changes.

- iPhone / iPad open the **field app** (index.html).
- The Mac opens the **Command Center** (desktop.html). Menu **BuildersPro** → ⌘1 Command Center, ⌘2 Field App, ⌘R Reload.
- Face ID opens the app (the web passcode screen is skipped inside the app).
- Share, Save, Print, pop-ups, camera and microphone all go to the real iPhone/Mac features.
- Sync is the web app's own sync (iCloud or GitHub). **One sync for everything.**

## First time on each device
The app keeps its own copy of your data, separate from Safari / the Home-Screen web app.
Open **Sync** in the app once and sign in (iCloud) or paste your pairing code (GitHub) — it pulls everything down.

## Building it (only when the native folder changes)
Double-click **Setup.command**, then press **Play ▶** in Xcode with your iPhone (or My Mac) selected.
Every push is compile-checked on a Mac in the cloud first (GitHub → Actions → "Native app compile check").

## Old SwiftData app
The earlier SwiftData rebuild is kept in `Legacy-SwiftData/` (not built). Anything entered in it
is still in iCloud container `iCloud.com.stanrobinson.builderspro` if it ever needs recovering.
