import Foundation
import Security
import WebKit

/// v6.4.0 — BSP's AI assistant. Stan's own Anthropic API key lives in the Keychain on this
/// iPhone / iPad / Mac (synced through iCloud Keychain when that is on). The web page never
/// sees the key: it sends { kind: 'ai', id, body } and gets the answer back through
/// window.bpAIDone(id, result). Calls go straight from the device to api.anthropic.com.
enum AIKey {
    private static let service = "com.stanrobinson.builderspro.ai"
    private static let account = "anthropic"
    /// v6.5.3: the last Keychain result, so the page can say why a save failed.
    static var lastStatus: OSStatus = errSecSuccess

    /// v6.5.3 — the Mac. An iCloud-synced Keychain item on macOS needs the "data protection" keychain;
    /// without it the save failed there and the Mac app kept saying there was no key. Try, in order:
    /// synced (iPhone ⇄ iPad ⇄ Mac), then this device only, then (Mac) the classic login keychain.
    private static func base(sync: Bool?, modern: Bool) -> [String: Any] {
        var q: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                kSecAttrService as String: service,
                                kSecAttrAccount as String: account]
        if let sync { q[kSecAttrSynchronizable as String] = sync ? kCFBooleanTrue as Any : kCFBooleanFalse as Any }
        else { q[kSecAttrSynchronizable as String] = kSecAttrSynchronizableAny }
        #if os(macOS)
        if modern { q[kSecUseDataProtectionKeychain as String] = true }
        #endif
        return q
    }
    private static var flavors: [Bool] {
        #if os(macOS)
        return [true, false]
        #else
        return [true]
        #endif
    }

    static func get() -> String? {
        for modern in flavors {
            var q = base(sync: nil, modern: modern)
            q[kSecReturnData as String] = true
            q[kSecMatchLimit as String] = kSecMatchLimitOne
            var out: CFTypeRef?
            if SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? Data {
                let s = String(data: d, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                if !s.isEmpty { return s }
            }
        }
        return nil
    }

    @discardableResult
    static func set(_ key: String) -> Bool {
        clear()
        let attempts: [(Bool, Bool)] = flavors.flatMap { m in [(true, m), (false, m)] }   // (sync, modern)
        for (sync, modern) in attempts {
            var q = base(sync: sync, modern: modern)
            q[kSecValueData as String] = Data(key.utf8)
            if modern || sync { q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock }
            lastStatus = SecItemAdd(q as CFDictionary, nil)
            if lastStatus == errSecSuccess { return true }
        }
        return false
    }

    static func clear() { for m in flavors { SecItemDelete(base(sync: nil, modern: m) as CFDictionary) } }
}

extension ShellModel {
    func aiMessage(_ kind: String, _ body: [String: Any]) {
        let reply: (String) -> Void = { [weak self] js in self?.webView.evaluateJavaScript(js) }
        switch kind {
        case "aiKeyStatus":
            reply("window.bpAIKeyStatus && bpAIKeyStatus(\(AIKey.get() != nil))")
        case "aiKeySet":
            let k = ((body["key"] as? String) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            let ok = !k.isEmpty && AIKey.set(k) && AIKey.get() != nil
            let why = ok ? "" : (k.isEmpty ? "No key was pasted" : "Keychain would not save it (code \(AIKey.lastStatus))")
            reply("window.bpAIKeyStatus && bpAIKeyStatus(\(ok), " + DailyBackup.js(why) + ")")
        case "aiKeyClear":
            AIKey.clear()
            reply("window.bpAIKeyStatus && bpAIKeyStatus(false)")
        default: // "ai"
            let id = (body["id"] as? String) ?? ""
            guard let req = body["body"] as? [String: Any] else { return }
            AIClient.send(req) { result in
                let js = "window.bpAIDone && bpAIDone(" + DailyBackup.js(id) + "," + SiteTools.json(result) + ")"
                Task { @MainActor in reply(js) }
            }
        }
    }
}

enum AIClient {
    static let url = URL(string: "https://api.anthropic.com/v1/messages")!
    /// Newest API version first; if the account's endpoint rejects it, retry once with the long-standing one.
    static let versions = ["2026-10-21", "2023-06-01"]

    static func send(_ body: [String: Any], attempt: Int = 0, done: @escaping ([String: Any]) -> Void) {
        guard let key = AIKey.get() else { done(["ok": false, "err": "nokey"]); return }
        guard let data = try? JSONSerialization.data(withJSONObject: body) else { done(["ok": false, "err": "Could not build the request"]); return }
        var r = URLRequest(url: url, timeoutInterval: 180)
        r.httpMethod = "POST"
        r.setValue(key, forHTTPHeaderField: "x-api-key")
        r.setValue(versions[min(attempt, versions.count - 1)], forHTTPHeaderField: "anthropic-version")
        r.setValue("application/json", forHTTPHeaderField: "content-type")
        r.httpBody = data
        URLSession.shared.dataTask(with: r) { d, resp, err in
            if let err { done(["ok": false, "err": err.localizedDescription]); return }
            let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
            let obj = (d.flatMap { try? JSONSerialization.jsonObject(with: $0) }) as? [String: Any] ?? [:]
            if code != 200 {
                let msg = ((obj["error"] as? [String: Any])?["message"] as? String) ?? "HTTP \(code)"
                if code == 400, attempt + 1 < versions.count, msg.lowercased().contains("version") {
                    send(body, attempt: attempt + 1, done: done); return
                }
                if code == 400, msg.lowercased().contains("workspace") {
                    done(["ok": false, "err": "This key needs a workspace. Make a new key and pick the Default workspace when you create it.", "status": code]); return
                }
                done(["ok": false, "err": code == 401 ? "The AI key was not accepted. Check it in Settings › AI." : msg, "status": code])
                return
            }
            let text = ((obj["content"] as? [[String: Any]]) ?? [])
                .filter { ($0["type"] as? String) == "text" }
                .compactMap { $0["text"] as? String }
                .joined()
            let usage = obj["usage"] as? [String: Any] ?? [:]
            done(["ok": true, "text": text, "usage": usage, "stop": obj["stop_reason"] as? String ?? ""])
        }.resume()
    }
}
