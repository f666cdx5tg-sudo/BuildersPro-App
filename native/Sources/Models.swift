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

    @Relationship(deleteRule: .cascade, inverse: \Space.job) var spaces: [Space]? = []
    @Relationship(deleteRule: .cascade, inverse: \PunchItem.job) var punchItems: [PunchItem]? = []
    @Relationship(deleteRule: .cascade, inverse: \SitePhoto.job) var photos: [SitePhoto]? = []

    init(name: String) { self.name = name }

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
