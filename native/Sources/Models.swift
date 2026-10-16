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
    var clientEmail: String = ""
    var clientPhone: String = ""
    var status: String = "Active"    // Active, Complete…
    var startDate: Date?
    var completionDate: Date?
    var jobNotes: String = ""

    @Relationship(deleteRule: .cascade, inverse: \Space.job) var spaces: [Space]? = []
    @Relationship(deleteRule: .cascade, inverse: \PunchItem.job) var punchItems: [PunchItem]? = []
    @Relationship(deleteRule: .cascade, inverse: \SitePhoto.job) var photos: [SitePhoto]? = []
    @Relationship(deleteRule: .cascade, inverse: \Expense.job) var expenses: [Expense]? = []
    @Relationship(deleteRule: .cascade, inverse: \Contractor.job) var contractors: [Contractor]? = []
    @Relationship(deleteRule: .cascade, inverse: \DailyReport.job) var reports: [DailyReport]? = []
    @Relationship(deleteRule: .cascade, inverse: \ChangeOrder.job) var changeOrders: [ChangeOrder]? = []
    @Relationship(deleteRule: .cascade, inverse: \Invoice.job) var invoices: [Invoice]? = []
    @Relationship(deleteRule: .cascade, inverse: \Permit.job) var permits: [Permit]? = []
    @Relationship(deleteRule: .cascade, inverse: \TimeEntry.job) var timeEntries: [TimeEntry]? = []
    @Relationship(deleteRule: .cascade, inverse: \Appointment.job) var appointments: [Appointment]? = []
    @Relationship(deleteRule: .cascade, inverse: \JobNote.job) var notes: [JobNote]? = []
    @Relationship(deleteRule: .cascade, inverse: \ShoppingItem.job) var shopping: [ShoppingItem]? = []
    @Relationship(deleteRule: .cascade, inverse: \JobDocument.job) var documents: [JobDocument]? = []

    init(name: String) { self.name = name }

    // Money — same math as the web app:
    // revised contract = contract + approved change orders; remaining = revised − (expenses + what you agreed to pay contractors)
    var expenseTotal: Double { (expenses ?? []).reduce(0) { $0 + $1.amount } }
    var contractorTotal: Double { (contractors ?? []).reduce(0) { $0 + $1.value } }
    var contractorPaid: Double { (contractors ?? []).reduce(0) { $0 + $1.paid } }
    var approvedChangeOrders: Double { (changeOrders ?? []).filter { $0.status == "Approved" }.reduce(0) { $0 + $1.amount } }
    var pendingChangeOrders: Double { (changeOrders ?? []).filter { $0.status == "Draft" || $0.status == "Submitted" }.reduce(0) { $0 + $1.amount } }
    var revisedContract: Double { contract + approvedChangeOrders }
    var totalCost: Double { expenseTotal + contractorTotal }
    var remaining: Double { revisedContract - totalCost }
    var marginPercent: Int { revisedContract > 0 ? Int((remaining / revisedContract * 100).rounded()) : 0 }
    var invoiced: Double { (invoices ?? []).reduce(0) { $0 + $1.amount } }
    var collected: Double { (invoices ?? []).filter { $0.status == "Paid" }.reduce(0) { $0 + $1.amount } }
    var outstanding: Double { (invoices ?? []).filter { $0.status == "Sent" || $0.status == "Overdue" }.reduce(0) { $0 + $1.amount } }
    var permitTotal: Double { (permits ?? []).reduce(0) { $0 + $1.cost } }
    var laborTotal: Double { (timeEntries ?? []).reduce(0) { $0 + $1.hours * $1.rate } }
    var laborHours: Double { (timeEntries ?? []).reduce(0) { $0 + $1.hours } }
    /// Cash actually gone out: expenses + payments made + permits + time-clock labor ("Total Spent" in the web app's Spending tab)
    var cashSpent: Double { expenseTotal + contractorPaid + permitTotal + laborTotal }

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
    var priority: String = ""       // High, Medium, Low or ""
    var extraNotes: String = ""
    var value: Double = 0
    var sourceID: String = ""
    @Relationship(deleteRule: .cascade, inverse: \PunchPhoto.item) var photos: [PunchPhoto]? = []

    init(text: String, trade: String) { self.text = text; self.trade = trade }
}

@Model
final class PunchPhoto {
    @Attribute(.externalStorage) var data: Data?
    var kind: String = "Before"      // Before, After, Completion
    var created: Date = Date()
    var item: PunchItem?

    init(data: Data?, kind: String) { self.data = data; self.kind = kind }
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
    var startDate: Date?
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

@Model
final class ChangeOrder {
    var number: String = ""                          // "CO-001"
    var title: String = ""
    var details: String = ""
    var amount: Double = 0                           // can be negative (a credit)
    var daysAdded: Int = 0
    var status: String = "Draft"                     // Draft, Submitted, Approved, Rejected, Void
    var reason: String = "Other"
    var date: Date = Date()
    var approvedBy: String = ""
    var approvedAt: Date?
    var sourceID: String = ""
    var job: Job?

    init(number: String) { self.number = number }
}

@Model
final class Invoice {
    var title: String = ""
    var amount: Double = 0
    var date: Date = Date()
    var status: String = "Draft"                     // Draft, Sent, Paid, Overdue
    var notes: String = ""
    var sourceID: String = ""
    var job: Job?

    init(title: String, amount: Double) { self.title = title; self.amount = amount }
}

@Model
final class Permit {
    var trade: String = "General"
    var number: String = ""
    var cost: Double = 0
    var issueDate: Date = Date()
    var expirationDate: Date = Date()
    var status: String = "Active"                    // Active, Pending, Closed
    var notes: String = ""
    var sourceID: String = ""
    var job: Job?

    init(trade: String) { self.trade = trade }
}

@Model
final class TimeEntry {
    var worker: String = ""
    var clockIn: Date = Date()
    var clockOut: Date = Date()
    var isOpen: Bool = false                         // still clocked in
    var rate: Double = 0                             // dollars per hour
    var notes: String = ""
    var sourceID: String = ""
    var job: Job?

    init(worker: String) { self.worker = worker }

    var hours: Double {
        let end = isOpen ? Date() : clockOut
        let h = end.timeIntervalSince(clockIn) / 3600
        return h > 0 ? (h * 100).rounded() / 100 : 0
    }
}

@Model
final class Appointment {
    var title: String = ""
    var kind: String = "Appointment"                 // Appointment, Delivery, Inspection, Meeting, Other
    var date: Date = Date()                          // date and time together
    var notes: String = ""
    var sourceID: String = ""
    var job: Job?

    init(title: String) { self.title = title }
}

@Model
final class JobNote {
    var title: String = ""
    var text: String = ""
    var author: String = ""
    var created: Date = Date()
    var sourceID: String = ""
    var job: Job?

    init(title: String) { self.title = title }
}

@Model
final class ShoppingItem {
    var text: String = ""
    var qty: Double = 1
    var unit: String = ""
    var price: Double = 0                            // price for one
    var store: String = ""
    var note: String = ""
    var bought: Bool = false
    var boughtAt: Date?
    var created: Date = Date()
    var sourceID: String = ""
    var job: Job?

    init(text: String) { self.text = text }

    var total: Double { qty * price }
}

@Model
final class Vendor {
    var name: String = ""
    var sourceID: String = ""

    init(name: String) { self.name = name }
}

@Model
final class JobDocument {
    var name: String = ""
    var category: String = "Other"                   // Contract, License, Inspection Report, Other…
    var fileName: String = ""
    var ext: String = "pdf"                          // extension used when previewing: pdf, jpg, png…
    var notes: String = ""
    var created: Date = Date()
    @Attribute(.externalStorage) var data: Data?
    var sourceID: String = ""
    var job: Job?

    init(name: String) { self.name = name }
}

enum Money {
    static func text(_ n: Double) -> String {
        let sign = n < 0 ? "-" : ""
        return sign + abs(n).formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }
    static let categories = ["Materials", "Labor", "Permits", "Equipment", "Other"]
    static let methods = ["Check", "Zelle", "Cash", "Credit Card", "Other"]
    static let coStatuses = ["Draft", "Submitted", "Approved", "Rejected", "Void"]
    static let coReasons = ["Owner request", "Field condition", "Design change", "Code / inspector",
                            "Hidden condition", "Scope clarification", "Other"]
    static let invoiceStatuses = ["Draft", "Sent", "Paid", "Overdue"]
    static let permitTrades = ["General", "Electrical", "Plumbing", "HVAC", "Framing", "Roofing", "Masonry", "Building", "Other"]
    static let permitStatuses = ["Active", "Pending", "Closed"]
    static let appointmentKinds = ["Appointment", "Due Date", "Delivery", "Inspection", "Meeting", "Other"]
    static let documentCategories = ["Contract", "License", "Insurance", "Inspection Report", "Permit", "Plans", "Other"]
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
