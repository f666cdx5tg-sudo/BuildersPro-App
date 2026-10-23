import SwiftUI

/// BuildersPro 6 — the native app is now a frame around the live web app.
/// Every fix pushed to GitHub shows up here on the next launch; no Xcode rebuild needed.
/// Native parts: Face ID (LockGate), share sheet, save, print, pop-ups, camera and mic permissions.
@main
struct BuildersProApp: App {
    @StateObject private var shell = ShellModel()

    var body: some Scene {
        WindowGroup {
            LockGate { ShellView(model: shell) }
        }
        #if os(macOS)
        .defaultSize(width: 1440, height: 920)
        .commands {
            CommandMenu("BuildersPro") {
                Button("Command Center") { shell.show(.command) }
                    .keyboardShortcut("1", modifiers: .command)
                Button("Field App") { shell.show(.field) }
                    .keyboardShortcut("2", modifiers: .command)
                Divider()
                Button("Reload") { shell.reload() }
                    .keyboardShortcut("r", modifiers: .command)
            }
        }
        #endif
    }
}
