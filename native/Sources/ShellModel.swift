import SwiftUI
import WebKit
import EventKit
#if os(iOS)
import UIKit
#else
import AppKit
#endif

/// Which web page the frame shows. iPhone/iPad open the field app; the Mac opens the Command Center.
enum BPPage: String {
    case field = "index.html"
    case command = "desktop.html"
}

/// Owns the one web view that holds the live BuildersPro web app, and answers everything
/// the page asks the device for: pop-up windows, alerts, share, save, print, camera and mic.
@MainActor
final class ShellModel: NSObject, ObservableObject {
    static let site = URL(string: "https://f666cdx5tg-sudo.github.io/BuildersPro-App/")!
    static let host = "f666cdx5tg-sudo.github.io"

    let webView: WKWebView
    @Published var popup: WKWebView?
    @Published var offline = false

    private(set) var page: BPPage
    private var triedCache = false

    override init() {
        #if os(macOS)
        page = .command
        #else
        page = .field
        #endif

        let cfg = WKWebViewConfiguration()
        cfg.websiteDataStore = .default()                       // keeps the app's saved data between launches
        cfg.preferences.javaScriptCanOpenWindowsAutomatically = true
        #if os(iOS)
        cfg.allowsInlineMediaPlayback = true
        cfg.mediaTypesRequiringUserActionForPlayback = []
        cfg.applicationNameForUserAgent = "Mobile/15E148 Safari/604.1 BuildersProShell"
        #else
        cfg.applicationNameForUserAgent = "Version/17.0 Safari/605.1.15 BuildersProShell"
        #endif

        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
        let ucc = WKUserContentController()
        ucc.addUserScript(WKUserScript(source: Bridge.startScript.replacingOccurrences(of: "__VERSION__", with: version),
                                       injectionTime: .atDocumentStart, forMainFrameOnly: true))
        cfg.userContentController = ucc

        webView = BPWebView(frame: .zero, configuration: cfg)
        super.init()

        ucc.add(WeakHandler(self), name: Bridge.handlerName)
        configure(webView)
        #if DEBUG
        if #available(iOS 16.4, macOS 13.3, *) { webView.isInspectable = true }
        #endif
        load(page)
    }

    private func configure(_ wv: WKWebView) {
        wv.navigationDelegate = self
        wv.uiDelegate = self
        wv.allowsBackForwardNavigationGestures = false
        wv.underPageBackgroundColor = .black
        #if os(iOS)
        wv.allowsLinkPreview = false                            // press-and-hold stays free for drag and drop
        wv.scrollView.contentInsetAdjustmentBehavior = .never   // the page handles the notch / Dynamic Island itself
        wv.isOpaque = false
        wv.backgroundColor = .black
        wv.scrollView.backgroundColor = .black
        #endif
    }

    // MARK: Loading

    func show(_ p: BPPage) { page = p; load(p) }
    func reload() { load(page) }

    /// Online: always fetch the newest version from GitHub so pushed fixes show up right away.
    /// Offline: fall back to the copy saved from the last successful launch.
    private func load(_ p: BPPage, fromCache: Bool = false) {
        offline = false
        triedCache = fromCache
        let url = Self.site.appendingPathComponent(p.rawValue)
        let req = URLRequest(url: url,
                             cachePolicy: fromCache ? .returnCacheDataDontLoad : .reloadIgnoringLocalCacheData,
                             timeoutInterval: fromCache ? 10 : 20)
        webView.load(req)
    }

    func closePopup() { popup = nil }

    // MARK: Messages from the page

    func handle(_ message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let kind = body["kind"] as? String else { return }
        let source = message.webView ?? webView
        switch kind {
        case "print":
            printPage(source)
        case "share", "save":
            let files = writeFiles(body["files"] as? [[String: Any]] ?? [])
            let text = body["text"] as? String ?? ""
            deliver(files: files, text: text, save: kind == "save", from: source)
        case "calendarSync":
            let evs = body["events"] as? [[String: Any]] ?? []
            CalendarSync.shared.sync(evs) { [weak self] js in self?.webView.evaluateJavaScript(js) }
        case "backupBegin", "backupChunk", "backupEnd":
            DailyBackup.shared.handle(kind, body, reply: { [weak self] js in self?.webView.evaluateJavaScript(js) })
        default:
            break
        }
    }

    private func writeFiles(_ list: [[String: Any]]) -> [URL] {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("bp-share-\(UUID().uuidString)", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        var out: [URL] = []
        for f in list {
            guard let b64 = f["b64"] as? String, let data = Data(base64Encoded: b64) else { continue }
            var name = (f["name"] as? String) ?? "file"
            name = name.replacingOccurrences(of: "/", with: "-").replacingOccurrences(of: ":", with: "-")
            if name.isEmpty { name = "file" }
            let url = dir.appendingPathComponent(name)
            if (try? data.write(to: url)) != nil { out.append(url) }
        }
        return out
    }

    static func isExternalScheme(_ url: URL) -> Bool {
        ["mailto", "tel", "sms", "facetime", "maps", "itms-apps"].contains(url.scheme?.lowercased() ?? "")
    }

    /// Sign-in pages that must stay inside the app because they report back to the page that opened them.
    static func staysInApp(_ url: URL) -> Bool {
        let h = url.host?.lowercased() ?? ""
        if h == host { return true }
        return ["apple.com", "icloud.com", "apple-cloudkit.com", "accounts.google.com"]
            .contains { h == $0 || h.hasSuffix("." + $0) }
    }

    func openExternal(_ url: URL) {
        #if os(iOS)
        UIApplication.shared.open(url)
        #else
        NSWorkspace.shared.open(url)
        #endif
    }

    // MARK: Share, save, print — iPhone / iPad

    #if os(iOS)
    private func topViewController() -> UIViewController? {
        let windows = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
        var vc = (windows.first { $0.isKeyWindow } ?? windows.first)?.rootViewController
        while let next = vc?.presentedViewController, !next.isBeingDismissed { vc = next }
        return vc
    }

    private func deliver(files: [URL], text: String, save: Bool, from source: WKWebView) {
        var items: [Any] = files
        if !text.isEmpty { items.append(text) }
        guard !items.isEmpty, let vc = topViewController() else { return }
        let sheet = UIActivityViewController(activityItems: items, applicationActivities: nil)
        if let pop = sheet.popoverPresentationController {           // iPad needs an anchor
            pop.sourceView = source
            pop.sourceRect = CGRect(x: source.bounds.midX, y: source.bounds.midY, width: 1, height: 1)
            pop.permittedArrowDirections = []
        }
        vc.present(sheet, animated: true)
    }

    func printPage(_ source: WKWebView) {
        let info = UIPrintInfo(dictionary: nil)
        info.outputType = .general
        info.jobName = source.title ?? "BuildersPro"
        let pc = UIPrintInteractionController.shared
        pc.printInfo = info
        pc.printFormatter = source.viewPrintFormatter()
        pc.present(animated: true, completionHandler: nil)
    }

    fileprivate func alert(_ message: String, buttons: [(String, UIAlertAction.Style)], field: String? = nil,
                           done: @escaping (Int, String?) -> Void) {
        // A pop-up that can't be shown must still answer, or the page waits forever (freeze).
        guard let vc = topViewController(), vc.view.window != nil, vc.presentedViewController == nil else {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { [weak self] in
                guard let self, let vc = self.topViewController(), vc.view.window != nil,
                      vc.presentedViewController == nil else { done(-1, nil); return }
                self.present(message, buttons: buttons, field: field, on: vc, done: done)
            }
            return
        }
        present(message, buttons: buttons, field: field, on: vc, done: done)
    }

    fileprivate func present(_ message: String, buttons: [(String, UIAlertAction.Style)], field: String?,
                             on vc: UIViewController, done: @escaping (Int, String?) -> Void) {
        let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        if let field { a.addTextField { $0.text = field } }
        for (i, b) in buttons.enumerated() {
            a.addAction(UIAlertAction(title: b.0, style: b.1) { _ in done(i, a.textFields?.first?.text) })
        }
        vc.present(a, animated: true)
    }
    #endif

    // MARK: Share, save, print — Mac

    #if os(macOS)
    private func deliver(files: [URL], text: String, save: Bool, from source: WKWebView) {
        if save || (files.count == 1 && text.isEmpty) {
            for f in files {
                let panel = NSSavePanel()
                panel.nameFieldStringValue = f.lastPathComponent
                panel.canCreateDirectories = true
                if panel.runModal() == .OK, let dest = panel.url {
                    try? FileManager.default.removeItem(at: dest)
                    try? FileManager.default.copyItem(at: f, to: dest)
                }
            }
            return
        }
        var items: [Any] = files
        if !text.isEmpty { items.append(text) }
        guard !items.isEmpty else { return }
        NSSharingServicePicker(items: items)
            .show(relativeTo: NSRect(x: source.bounds.midX, y: source.bounds.midY, width: 1, height: 1),
                  of: source, preferredEdge: .minY)
    }

    func printPage(_ source: WKWebView) {
        let info = NSPrintInfo.shared
        let op = source.printOperation(with: info)
        op.view?.frame = source.bounds        // without this the pages come out blank
        if let w = source.window {
            op.runModal(for: w, delegate: nil, didRun: nil, contextInfo: nil)
        } else {
            op.run()
        }
    }
    #endif
}

// MARK: - Page loading and links

extension ShellModel: WKNavigationDelegate {
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.allow); return }
        if Self.isExternalScheme(url) { openExternal(url); decisionHandler(.cancel); return }
        let scheme = url.scheme?.lowercased() ?? ""
        // Pop-up windows (sign-in, reports) and anything inside frames go wherever they need to.
        if webView !== self.webView || navigationAction.targetFrame?.isMainFrame != true || scheme != "http" && scheme != "https" {
            decisionHandler(.allow); return
        }
        if Self.staysInApp(url) { decisionHandler(.allow); return }
        // Any other website the app links to opens in Safari, so the app itself never gets lost.
        openExternal(url)
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if webView === self.webView { offline = false; triedCache = false }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        guard webView === self.webView else { return }
        let ns = error as NSError
        if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled { return }
        if !triedCache { load(page, fromCache: true) } else { offline = true }
    }

    /// iOS sometimes ends a web view's process while the app sits in the background — reload instead of a blank screen.
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        if webView === self.webView { reload() } else { closePopup() }
    }
}

// MARK: - Pop-ups, alerts, camera, file picker

extension ShellModel: WKUIDelegate {
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url {
            if Self.isExternalScheme(url) { openExternal(url); return nil }
            let s = url.scheme?.lowercased() ?? ""
            if (s == "http" || s == "https") && !Self.staysInApp(url) { openExternal(url); return nil }
        }
        let pop = WKWebView(frame: .zero, configuration: configuration)
        configure(pop)
        popup = pop
        return pop
    }

    func webViewDidClose(_ webView: WKWebView) {
        if webView === popup { closePopup() }
    }

    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.grant)   // iOS / macOS still ask you once for camera and microphone access
    }

    #if os(iOS)
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        alert(message, buttons: [("OK", .default)]) { _, _ in completionHandler() }
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        alert(message, buttons: [("Cancel", .cancel), ("OK", .default)]) { i, _ in completionHandler(i == 1) }
    }

    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        alert(prompt, buttons: [("Cancel", .cancel), ("OK", .default)], field: defaultText ?? "") { i, text in
            completionHandler(i == 1 ? (text ?? "") : nil)
        }
    }
    #else
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = message; a.addButton(withTitle: "OK")
        a.runModal(); completionHandler()
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = message
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        completionHandler(a.runModal() == .alertFirstButtonReturn)
    }

    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert(); a.messageText = prompt
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        field.stringValue = defaultText ?? ""
        a.accessoryView = field
        completionHandler(a.runModal() == .alertFirstButtonReturn ? field.stringValue : nil)
    }

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let p = NSOpenPanel()
        p.allowsMultipleSelection = parameters.allowsMultipleSelection
        p.canChooseDirectories = parameters.allowsDirectories
        p.canChooseFiles = true
        p.begin { r in completionHandler(r == .OK ? p.urls : nil) }
    }
    #endif
}

/// Keeps the page's message channel from holding the app's web model alive forever.
@MainActor
final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: ShellModel?
    init(_ target: ShellModel) { self.target = target }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        target?.handle(message)
    }
}


// MARK: Daily backup file (v6.1.15)

/// The page streams a full backup (records + every photo) in pieces; this writes it to
/// iCloud Drive › BuildersPro › Backups (or, if iCloud Drive is off, Files › On My iPhone ›
/// BuildersPro › Backups) and keeps the newest 30. The same JSON the Restore button reads.
final class DailyBackup {
    static let shared = DailyBackup()
    static let containerID = "iCloud.com.stanleyrobinson.builderspro"
    private let q = DispatchQueue(label: "bp.backup")
    private var fh: FileHandle?
    private var tmp: URL?
    private var name = ""
    private var bytes = 0

    func handle(_ kind: String, _ body: [String: Any], reply: @escaping @MainActor (String) -> Void) {
        q.async { [self] in
            switch kind {
            case "backupBegin":
                try? fh?.close()
                name = ((body["name"] as? String) ?? "builderspro-backup.json")
                    .replacingOccurrences(of: "/", with: "-").replacingOccurrences(of: ":", with: "-")
                let t = FileManager.default.temporaryDirectory.appendingPathComponent("bp-backup-\(UUID().uuidString).json")
                FileManager.default.createFile(atPath: t.path, contents: nil)
                tmp = t; bytes = 0
                fh = try? FileHandle(forWritingTo: t)
            case "backupChunk":
                if let s = body["text"] as? String, let d = s.data(using: .utf8) {
                    fh?.write(d); bytes += d.count
                }
            default: // backupEnd
                try? fh?.close(); fh = nil
                let result = finish()
                let js = "window.bpBackupDone && window.bpBackupDone(" + result + ")"
                Task { @MainActor in reply(js) }
            }
        }
    }

    private func folder() -> (URL, String)? {
        let fm = FileManager.default
        if let c = fm.url(forUbiquityContainerIdentifier: Self.containerID) {
            let d = c.appendingPathComponent("Documents/Backups", isDirectory: true)
            if (try? fm.createDirectory(at: d, withIntermediateDirectories: true)) != nil { return (d, "iCloud Drive › BuildersPro › Backups") }
        }
        if let docs = fm.urls(for: .documentDirectory, in: .userDomainMask).first {
            let d = docs.appendingPathComponent("Backups", isDirectory: true)
            if (try? fm.createDirectory(at: d, withIntermediateDirectories: true)) != nil {
                #if os(iOS)
                return (d, "Files › On My iPhone › BuildersPro › Backups")
                #else
                return (d, d.path)
                #endif
            }
        }
        return nil
    }

    private func finish() -> String {
        let fm = FileManager.default
        guard let t = tmp, bytes > 0, let f = folder() else {
            return "{ok:false,err:'could not create the backup folder'}"
        }
        let dir = f.0, label = f.1
        let dest = dir.appendingPathComponent(name)
        try? fm.removeItem(at: dest)
        do { try fm.moveItem(at: t, to: dest) } catch {
            return "{ok:false,err:" + Self.js(error.localizedDescription) + "}"
        }
        // keep the newest 30
        if let all = try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey]) {
            let files = all.filter { $0.pathExtension == "json" }.sorted {
                let a = (try? $0.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                let b = (try? $1.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                return a > b
            }
            for old in files.dropFirst(30) { try? fm.removeItem(at: old) }
        }
        return "{ok:true,where:" + Self.js(label) + ",name:" + Self.js(name) + ",bytes:\(bytes)}"
    }

    static func js(_ s: String) -> String {
        let d = (try? JSONSerialization.data(withJSONObject: [s])) ?? Data("[\"\"]".utf8)
        let a = String(data: d, encoding: .utf8) ?? "[\"\"]"
        return String(a.dropFirst().dropLast())
    }
}


// MARK: Calendar (v6.1.16)

/// Keeps a calendar called "BuildersPro" in the phone's own Calendar app matching the
/// app's appointments. It lives in the iCloud account when there is one, so it shows on
/// the Mac and iPad too. One way: BuildersPro → Calendar. Only events this app made
/// (marked with its id) are ever changed or removed; nothing else in Calendar is touched.
@MainActor
final class CalendarSync {
    static let shared = CalendarSync()
    private let store = EKEventStore()
    private let tag = "builderspro://appt/"

    func sync(_ events: [[String: Any]], reply: @escaping @MainActor (String) -> Void) {
        Task { @MainActor in
            let granted: Bool
            do {
                if #available(iOS 17.0, macOS 14.0, *) { granted = try await store.requestFullAccessToEvents() }
                else { granted = try await store.requestAccess(to: .event) }
            } catch { granted = false }
            guard granted else { reply("window.bpCalDone && bpCalDone({ok:false,err:'Calendar access is off. Turn it on in Settings › BuildersPro › Calendars.'})"); return }
            guard let cal = calendar() else { reply("window.bpCalDone && bpCalDone({ok:false,err:'Could not create the BuildersPro calendar.'})"); return }

            let start = Date().addingTimeInterval(-400 * 86400), end = Date().addingTimeInterval(800 * 86400)
            let existing = store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: [cal]))
            var byId: [String: EKEvent] = [:]
            for e in existing { if let u = e.url?.absoluteString, u.hasPrefix(tag) { let k = String(u.dropFirst(tag.count)); byId[k.removingPercentEncoding ?? k] = e } }

            let iso = ISO8601DateFormatter()
            let day = DateFormatter(); day.dateFormat = "yyyy-MM-dd"; day.timeZone = .current
            var seen = Set<String>(), added = 0, changed = 0, removed = 0
            for ev in events {
                guard let id = ev["id"] as? String, !id.isEmpty else { continue }
                let allDay = (ev["allDay"] as? Bool) ?? true
                var s: Date?, f: Date?
                if allDay, let d = ev["date"] as? String, let dd = day.date(from: d) { s = dd; f = dd.addingTimeInterval(86400 - 1) }
                else if let a = ev["start"] as? String, let b = ev["end"] as? String { s = iso.date(from: a); f = iso.date(from: b) }
                guard let st = s, let en = f else { continue }
                seen.insert(id)
                let e = byId[id] ?? EKEvent(eventStore: store)
                let isNew = byId[id] == nil
                let title = (ev["title"] as? String) ?? "Appointment"
                let loc = (ev["location"] as? String) ?? ""
                let notes = (ev["notes"] as? String) ?? ""
                if !isNew && e.title == title && e.startDate == st && e.endDate == en && e.isAllDay == allDay
                    && (e.location ?? "") == loc && (e.notes ?? "") == notes { continue }
                e.calendar = cal; e.title = title; e.startDate = st; e.endDate = en; e.isAllDay = allDay
                e.location = loc.isEmpty ? nil : loc; e.notes = notes.isEmpty ? nil : notes
                e.url = URL(string: tag + (id.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? id))
                if (try? store.save(e, span: .thisEvent, commit: false)) != nil { if isNew { added += 1 } else { changed += 1 } }
            }
            for (id, e) in byId where !seen.contains(id) {
                if (try? store.remove(e, span: .thisEvent, commit: false)) != nil { removed += 1 }
            }
            try? store.commit()
            let where_ = cal.source.sourceType == .calDAV ? "iCloud" : "this device"
            reply("window.bpCalDone && bpCalDone({ok:true,total:\(seen.count),added:\(added),changed:\(changed),removed:\(removed),where:'\(where_)'})")
        }
    }

    private func calendar() -> EKCalendar? {
        let key = "bp_calendar_id"
        if let id = UserDefaults.standard.string(forKey: key), let c = store.calendar(withIdentifier: id) { return c }
        if let c = store.calendars(for: .event).first(where: { $0.title == "BuildersPro" && $0.allowsContentModifications }) {
            UserDefaults.standard.set(c.calendarIdentifier, forKey: key); return c
        }
        let c = EKCalendar(for: .event, eventStore: store)
        c.title = "BuildersPro"
        #if os(iOS)
        c.cgColor = UIColor(red: 0.04, green: 0.52, blue: 1.0, alpha: 1).cgColor
        #else
        c.color = NSColor(red: 0.04, green: 0.52, blue: 1.0, alpha: 1)
        #endif
        let icloud = store.sources.first { $0.sourceType == .calDAV && $0.title.lowercased().contains("icloud") }
        let src = icloud ?? store.defaultCalendarForNewEvents?.source ?? store.sources.first { $0.sourceType == .local }
        guard let s = src else { return nil }
        c.source = s
        do { try store.saveCalendar(c, commit: true) } catch { return nil }
        UserDefaults.standard.set(c.calendarIdentifier, forKey: key)
        return c
    }
}

/// The app's web view. On the Mac, a trackpad pinch never reaches the page on its own
/// (WKWebView keeps it for page magnification, which is off), so it is handed to the
/// photo viewer's zoom (window.bpPhotoPinch, v6.1.18). iPhone/iPad pinch reaches the page directly.
final class BPWebView: WKWebView {
    #if os(macOS)
    override func magnify(with event: NSEvent) {
        let p = convert(event.locationInWindow, from: nil)
        let y = isFlipped ? p.y : bounds.height - p.y
        let scale = max(0.2, 1 + event.magnification)
        evaluateJavaScript("window.bpPhotoPinch ? window.bpPhotoPinch(\(scale), \(p.x), \(y)) : false", completionHandler: nil)
    }
    #endif
}
