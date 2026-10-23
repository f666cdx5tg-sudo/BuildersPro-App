import XCTest
@testable import BuildersPro

/// Trades, levels, estimates and the other fixed lists the app depends on.
final class CatalogTests: XCTestCase {
    func testTradesIncludeDemoAndProtection() {
        XCTAssertTrue(Trades.all.contains("Demo"))
        XCTAssertTrue(Trades.all.contains("Protection"))
        XCTAssertEqual(Trades.symbol("Demo"), "xmark.bin")
        XCTAssertEqual(Trades.symbol("Protection"), "shield")
    }

    func testTradesHaveNoDuplicatesAndEndWithOther() {
        XCTAssertEqual(Set(Trades.all).count, Trades.all.count)
        XCTAssertEqual(Trades.all.last, "Other")
    }

    func testEveryTradeHasASymbol() {
        for t in Trades.all { XCTAssertFalse(Trades.symbol(t).isEmpty, t) }
    }

    func testLevelsSortBasementToOutside() {
        let sorted = ["Outside", "Level 2", "Basement", "Level 1", "Roof"].sorted { Levels.rank($0) < Levels.rank($1) }
        XCTAssertEqual(sorted, ["Basement", "Level 1", "Level 2", "Roof", "Outside"])
        XCTAssertEqual(Levels.title(""), "Level not set")
    }

    func testUnknownLevelSortsLast() {
        XCTAssertGreaterThan(Levels.rank("Attic"), Levels.rank("Outside"))
    }

    func testChangeOrderStatusesMatchWeb() {
        XCTAssertEqual(Money.coStatuses, ["Draft", "Submitted", "Approved", "Rejected", "Void"])
        XCTAssertEqual(Money.invoiceStatuses, ["Draft", "Sent", "Paid", "Overdue"])
    }

    func testEstimateTotalAndRoundTrip() {
        let e = Estimate(title: "Kitchen")
        e.lines = [EstimateLine(desc: "Cabinets", qty: 2, price: 1_500), EstimateLine(desc: "Install", qty: 1, price: 750.50)]
        XCTAssertEqual(e.total, 3_750.50, accuracy: 0.001)
        XCTAssertEqual(e.lines.count, 2)
        XCTAssertEqual(e.lines.first?.desc, "Cabinets")
    }

    func testEmptyEstimateHasZeroTotal() {
        XCTAssertEqual(Estimate(title: "x").total, 0)
        XCTAssertTrue(Estimate(title: "x").lines.isEmpty)
    }

    func testRoomIconAlwaysResolves() {
        for n in ["Kitchen", "Primary Bedroom", "Half Bath", "Laundry", "Garage", "Zzz unknown"] {
            XCTAssertFalse(RoomIcon.first(RoomIcon.candidates(for: n, stored: "")).isEmpty, n)
        }
    }
}
