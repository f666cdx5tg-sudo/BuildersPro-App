import AppIntents
import Foundation

/// v6.9.23 — Rent statements for the Shortcuts app.
/// iOS never lets an app send a text or email by itself, and an app doesn't wake up on a date.
/// The Shortcuts app can do both: a Personal Automation on the 25th runs "Get Rent Statements",
/// then "Send Message" / "Send Email" for each one.
/// The page hands the statements over every time Rentals changes ({ kind: 'rentStatements', items }).
/// They are kept here so the action works without opening BuildersPro.
/// Statements are written for next month and the month after, so the right one is ready on the 25th
/// even if the app hasn't been opened since. Balances are as of the last time the app was open.
enum RentStatementStore {
    private static let itemsKey = "bp.rentStatements.v1"
    private static let sentKey = "bp.rentStatements.sent.v1"

    struct Item: Codable {
        var unitId: String
        var month: String      // "2026-12"
        var tenant: String
        var unit: String
        var phone: String
        var email: String
        var subject: String
        var body: String
    }

    static func save(_ raw: [[String: Any]]) {
        let items: [Item] = raw.compactMap { d in
            guard let u = d["unitId"] as? String, let m = d["month"] as? String, let b = d["body"] as? String else { return nil }
            return Item(unitId: u, month: m, tenant: d["tenant"] as? String ?? "", unit: d["unit"] as? String ?? "",
                        phone: d["phone"] as? String ?? "", email: d["email"] as? String ?? "",
                        subject: d["subject"] as? String ?? "Rent statement", body: b)
        }
        if let data = try? JSONEncoder().encode(items) { UserDefaults.standard.set(data, forKey: itemsKey) }
    }

    static func load() -> [Item] {
        guard let data = UserDefaults.standard.data(forKey: itemsKey),
              let items = try? JSONDecoder().decode([Item].self, from: data) else { return [] }
        return items
    }

    /// "unitId|month" → "yyyy-MM-dd" sent date
    static func sent() -> [String: String] {
        (UserDefaults.standard.dictionary(forKey: sentKey) as? [String: String]) ?? [:]
    }

    static func markSent(_ items: [Item]) {
        var s = sent()
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"; f.locale = Locale(identifier: "en_US_POSIX")
        let today = f.string(from: Date())
        for i in items { s[i.unitId + "|" + i.month] = today }
        UserDefaults.standard.set(s, forKey: sentKey)
    }

    /// Next month as "yyyy-MM".
    static func nextMonth() -> String {
        let cal = Calendar(identifier: .gregorian)
        let d = cal.date(byAdding: .month, value: 1, to: Date()) ?? Date()
        let c = cal.dateComponents([.year, .month], from: d)
        return String(format: "%04d-%02d", c.year ?? 2026, c.month ?? 1)
    }

    /// The sent log as JSON for the page, so its "Sent" marks match.
    static func sentJSON() -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: sent()), let s = String(data: data, encoding: .utf8) else { return "{}" }
        return s
    }
}

struct RentStatementEntity: AppEntity, Identifiable {
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Rent Statement"
    static var defaultQuery = RentStatementQuery()

    var id: String
    @Property(title: "Tenant") var tenant: String
    @Property(title: "Unit") var unit: String
    @Property(title: "Phone") var phone: String
    @Property(title: "Email") var email: String
    @Property(title: "Subject") var subject: String
    @Property(title: "Message") var message: String
    @Property(title: "Month") var month: String

    init(_ i: RentStatementStore.Item) {
        id = i.unitId + "|" + i.month
        tenant = i.tenant; unit = i.unit; phone = i.phone; email = i.email
        subject = i.subject; message = i.body; month = i.month
    }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(tenant) · \(unit)", subtitle: "\(month)")
    }
}

struct RentStatementQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [RentStatementEntity] {
        RentStatementStore.load().map(RentStatementEntity.init).filter { identifiers.contains($0.id) }
    }
    func suggestedEntities() async throws -> [RentStatementEntity] {
        let m = RentStatementStore.nextMonth()
        return RentStatementStore.load().filter { $0.month == m }.map(RentStatementEntity.init)
    }
}

struct GetRentStatementsIntent: AppIntent {
    static var title: LocalizedStringResource = "Get Rent Statements"
    static var description = IntentDescription("Next month's rent statement for every tenant in BuildersPro Rentals. Use with Send Message or Send Email.")
    static var openAppWhenRun: Bool = false

    @Parameter(title: "Only ones not sent yet", default: true)
    var onlyUnsent: Bool

    @Parameter(title: "Mark as sent", default: true)
    var markSent: Bool

    static var parameterSummary: some ParameterSummary {
        Summary("Get rent statements") {
            \.$onlyUnsent
            \.$markSent
        }
    }

    func perform() async throws -> some IntentResult & ReturnsValue<[RentStatementEntity]> {
        let m = RentStatementStore.nextMonth()
        let sent = RentStatementStore.sent()
        var items = RentStatementStore.load().filter { $0.month == m }
        if onlyUnsent { items = items.filter { sent[$0.unitId + "|" + $0.month] == nil } }
        if markSent { RentStatementStore.markSent(items) }
        return .result(value: items.map(RentStatementEntity.init))
    }
}

struct BuildersProShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: GetRentStatementsIntent(),
                    phrases: ["Get rent statements in \(.applicationName)",
                              "\(.applicationName) rent statements"],
                    shortTitle: "Rent Statements",
                    systemImageName: "house")
    }
}
