import SwiftUI
import LocalAuthentication

/// Opens the app by itself the moment Face ID (or Touch ID on a Mac) recognizes you — no button to tap.
/// If recognition fails or you dismiss it, the iPhone's own passcode sheet is the backup, and a plain
/// "Unlock" button appears so you can try again. Nothing here ever sees or stores your face.
@MainActor
final class AppLock: ObservableObject {
    @Published var unlocked = false
    @Published var needsManualRetry = false

    /// How long the app can sit in the background before it locks again.
    static let relockAfter: TimeInterval = 60

    private var running = false
    private var leftAt: Date?

    func unlock() {
        guard !unlocked, !running else { return }
        running = true
        needsManualRetry = false
        let ctx = LAContext()
        var error: NSError?
        // Face ID / Touch ID first; the device passcode is the built-in fallback.
        guard ctx.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) else {
            // This device has no passcode at all, so there is nothing to check against.
            unlocked = true
            running = false
            return
        }
        Task {
            do {
                let ok = try await ctx.evaluatePolicy(.deviceOwnerAuthentication,
                                                      localizedReason: "Open BuildersPro")
                unlocked = ok
                needsManualRetry = !ok
            } catch {
                needsManualRetry = true   // cancelled or failed: wait for a deliberate tap, never loop
            }
            running = false
        }
    }

    func scenePhaseChanged(_ phase: ScenePhase) {
        switch phase {
        case .background:
            if leftAt == nil { leftAt = Date() }
        case .active:
            if let t = leftAt, Date().timeIntervalSince(t) > Self.relockAfter { unlocked = false }
            leftAt = nil
            unlock()   // no-op when already unlocked or already prompting
        default:
            break      // .inactive also happens while the Face ID sheet is up — ignore it
        }
    }
}

struct LockGate<Content: View>: View {
    @StateObject private var lock = AppLock()
    @Environment(\.scenePhase) private var phase
    @ViewBuilder var content: () -> Content

    var body: some View {
        // The app stays in place underneath, so re-locking never loses where you were.
        // No .allowsHitTesting here: switching it off and back on around the web view can leave
        // the page deaf to taps after Face ID / Touch ID (the "frozen after unlock" bug, v6.0.2).
        // The opaque lock screen on top already blocks every touch while locked.
        content()
            .accessibilityHidden(!lock.unlocked)
            .overlay {
                if !lock.unlocked { LockScreen(lock: lock) }
            }
            .task { lock.unlock() }
            .onChange(of: phase) { _, new in lock.scenePhaseChanged(new) }
    }
}

private struct LockScreen: View {
    @ObservedObject var lock: AppLock

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
                .contentShape(Rectangle())
                .onTapGesture { }          // swallow taps so nothing reaches the app underneath
            VStack(spacing: 18) {
                ZStack {
                    Circle().stroke(.white.opacity(0.94), lineWidth: 4).frame(width: 96, height: 96)
                    Text("B").font(.system(size: 52, weight: .bold, design: .serif)).foregroundStyle(.white.opacity(0.94))
                }
                Text("BuildersPro").font(.title2.bold()).foregroundStyle(.white)
                if lock.needsManualRetry {
                    Button { lock.unlock() } label: {
                        Label("Unlock", systemImage: "lock.fill")
                            .font(.headline).frame(maxWidth: 260).padding(.vertical, 14)
                    }
                    .buttonStyle(.borderedProminent)
                    .padding(.top, 8)
                }
            }
        }
    }
}
