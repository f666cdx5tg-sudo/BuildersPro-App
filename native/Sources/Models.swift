import Foundation
import SwiftData

// Every property has a default and every relationship is optional: CloudKit (iCloud sync) requires that.

@Model
final class Job {
    var name: String = ""
    var client: String = ""
    var address: String = ""
    var isActive: Bool = true
    var created: Date = Date()
    var sourceID: String = ""        // id from the old web app backup, so importing twice never duplicates
    var contract: Double = 0         // contract value in dollars

    @Relationship(deleteRule: .cascade, inverse: \Space.job) var spaces: [Space]? = []
    @Relationship(deleteRule: .cascade, inverse: \PunchItem.job) var punchItems: [PunchItem]? = []
    @Relationship(deleteRule: .cascade, inverse: \SitePhoto.job) var photos: [SitePhoto]? = []
    @Relationship(deleteRule: .cascade, inverse: \Expense.job) var expenses: [Expense]? = []
    @Relationship(deleteRule: .cascade, inverse: \Contractor.job) var contractors: [Contractor]? = []
    @Relationship(deleteRule: .cascade, inverse: \DailyReport.job) var reports: [DailyReport]? = []

    init(name: String) { self.name = name }

    // Money — same math as the web app: remaining = contract − (expenses + what you agreed to pay contractors)
    var expenseTotal: Double { (expenses ?? []).reduce(0) { $0 + $1.amount } }
    var contractorTotal: Double { (contractors ?? []).reduce(0) { $0 + $1.value } }
    var contractorPaid: Double { (contractors ?? []).reduce(0) { $0 + $1.paid } }
    var totalCost: Double { expenseTotal + contractorTotal }
    var remaining: Double { contract - totalCost }
    var marginPercent: Int { contract > 0 ? Int((remaining / contract * 100).rounded()) : 0 }

    var doneCount: Int { (punchItems ?? []).filter { $0.done }.count }
    var totalCount: Int { (punchItems ?? []).count }
    var percent: Int { totalCount == 0 ? 0 : Int((Double(doneCount) / Double(totalCount) * 100).rounded()) }
}

@Model
final class Space {
    var uid: UUID = UUID()
    var name: String = ""
    var level: String = ""          // "Basement", "Level 1"…, "Roof", "Outside", or "" (not set)
    var order: Int = 0              // position inside its level
    var isExterior: Bool = false
    var symbol: String = "square.split.bottomrightquarter"
    var job: Job?

    @Relationship(deleteRule: .cascade, inverse: \PunchItem.space) var punchItems: [PunchItem]? = []
    @Relationship(deleteRule: .nullify, inverse: \SitePhoto.space) var photos: [SitePhoto]? = []

    init(name: String, level: String = "", order: Int = 0, isExterior: Bool = false) {
        self.name = name; self.level = level; self.order = order; self.isExterior = isExterior
    }

    var openCount: Int { (punchItems ?? []).filter { !$0.done }.count }
    var doneCount: Int { (punchItems ?? []).filter { $0.done }.count }
    var photoCount: Int { (photos ?? []).count }
}

@Model
final class PunchItem {
    var text: String = ""
    var trade: String = ""
    var done: Bool = false
    var created: Date = Date()
    var completed: Date?
    var space: Space?               // nil = "General"
    var job: Job?

    init(text: String, trade: String) { self.text = text; self.trade = trade }
}

@Model
final class SitePhoto {
    @Attribute(.externalStorage) var data: Data?     // big files live outside the database
    var caption: String = ""
    var created: Date = Date()
    var space: Space?               // nil = Unfiled
    var job: Job?

    init(data: Data?) { self.data = data }
}

@Model
final class Expense {
    var title: String = ""
    var vendor: String = ""
    var category: String = ""
    var amount: Double = 0
    var date: Date = Date()
    var itemsText: String = ""                       // one line per item: "Trash — 250.00"
    @Attribute(.externalStorage) var receipt: Data?
    var sourceID: String = ""
    var job: Job?

    init(title: String, amount: Double) { self.title = title; self.amount = amount }
}

@Model
final class Contractor {
    var name: String = ""
    var trade: String = ""
    var value: Double = 0                            // what you agreed to pay
    var scope: String = ""
    var phone: String = ""
    var status: String = "Active"
    var sourceID: String = ""
    var job: Job?

    @Relationship(deleteRule: .cascade, inverse: \Payment.contractor) var payments: [Payment]? = []

    init(name: String) { self.name = name }

    var paid: Double { (payments ?? []).reduce(0) { $0 + $1.amount } }
    var owed: Double { value - paid }
}

@Model
final class Payment {
    var amount: Double = 0
    var date: Date = Date()
    var method: String = "Check"
    var notes: String = ""
    var contractor: Contractor?

    init(amount: Double) { self.amount = amount }
}

@Model
final class DailyReport {
    var number: String = ""                          // "DPR-001"
    var date: Date = Date()
    var workers: Int = 0
    var hours: String = ""
    var weather: String = ""
    var completed: String = ""
    var incomplete: String = ""
    var tomorrow: String = ""
    var visitors: String = ""
    var safety: String = ""
    var clientNotes: String = ""
    var progress: Int = 0
    var sourceID: String = ""
    var job: Job?

    init(number: String) { self.number = number }
}

enum Money {
    static func text(_ n: Double) -> String {
        let sign = n < 0 ? "-" : ""
        return sign + abs(n).formatted(.currency(code: "USD").precision(.fractionLength(0...2)))
    }
    static let categories = ["Materials", "Labor", "Permits", "Equipment", "Other"]
    static let methods = ["Check", "Zelle", "Cash", "Credit Card", "Other"]
}

enum Levels {
    static let all = ["Basement", "Level 1", "Level 2", "Level 3", "Level 4", "Roof", "Outside", ""]
    static func rank(_ l: String) -> Int { all.firstIndex(of: l) ?? all.count }
    static func title(_ l: String) -> String { l.isEmpty ? "Level not set" : l }
}

enum Trades {
    static let all = ["Plumbing", "Electrical", "Carpentry", "HVAC", "Masonry", "Drywall", "Painting",
                      "Tile/Flooring", "Roofing", "Windows/Doors", "Cleaning", "Other"]
    static func symbol(_ t: String) -> String {
        switch t {
        case "Plumbing": return "wrench.and.screwdriver"
        case "Electrical": return "bolt"
        case "Carpentry": return "hammer"
        case "HVAC": return "fan"
        case "Painting": return "paintbrush"
        case "Roofing": return "house"
        case "Windows/Doors": return "door.left.hand.closed"
        case "Cleaning": return "sparkles"
        default: return "square.grid.2x2"
        }
    }
}
