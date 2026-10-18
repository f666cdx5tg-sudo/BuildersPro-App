import XCTest
import SwiftData
@testable import BuildersPro

/// Money and job math. Mirrors the web app's formulas (revised contract, remaining, margin, billing, cash spent).
@MainActor
final class ModelMathTests: XCTestCase {
    var container: ModelContainer!
    var ctx: ModelContext!

    override func setUp() async throws {
        let schema = Schema([Job.self, Space.self, PunchItem.self, PunchPhoto.self, SitePhoto.self, Expense.self,
                             Contractor.self, Payment.self, DailyReport.self, ChangeOrder.self, Invoice.self, Permit.self,
                             TimeEntry.self, Appointment.self, JobNote.self, ShoppingItem.self, Vendor.self,
                             JobDocument.self, Estimate.self])
        container = try ModelContainer(for: schema, configurations: [ModelConfiguration(isStoredInMemoryOnly: true)])
        ctx = ModelContext(container)
    }

    private func job(contract: Double = 10_000) -> Job {
        let j = Job(name: "Test"); j.contract = contract; ctx.insert(j); return j
    }

    func testRevisedContractCountsOnlyApprovedChangeOrders() {
        let j = job()
        let a = ChangeOrder(number: "CO-1"); a.amount = 1_000; a.status = "Approved"
        let b = ChangeOrder(number: "CO-2"); b.amount = 500; b.status = "Draft"
        let c = ChangeOrder(number: "CO-3"); c.amount = -200; c.status = "Approved"      // a credit
        let d = ChangeOrder(number: "CO-4"); d.amount = 900; d.status = "Rejected"
        [a, b, c, d].forEach { ctx.insert($0); $0.job = j }
        XCTAssertEqual(j.approvedChangeOrders, 800)
        XCTAssertEqual(j.pendingChangeOrders, 500)
        XCTAssertEqual(j.revisedContract, 10_800)
    }

    func testRemainingMarginAndPercent() {
        let j = job(contract: 10_000)
        let e = Expense(title: "Lumber", amount: 2_000); ctx.insert(e); e.job = j
        let c = Contractor(name: "Sparky"); c.value = 3_000; ctx.insert(c); c.job = j
        XCTAssertEqual(j.totalCost, 5_000)
        XCTAssertEqual(j.remaining, 5_000)
        XCTAssertEqual(j.marginPercent, 50)
    }

    func testOverBudgetGivesNegativeRemaining() {
        let j = job(contract: 1_000)
        let e = Expense(title: "Big", amount: 1_500); ctx.insert(e); e.job = j
        XCTAssertEqual(j.remaining, -500)
        XCTAssertEqual(j.marginPercent, -50)
    }

    func testMarginIsZeroWithNoContract() {
        let j = job(contract: 0)
        XCTAssertEqual(j.marginPercent, 0)
    }

    func testBillingBuckets() {
        let j = job()
        for (amt, st) in [(100.0, "Paid"), (200.0, "Sent"), (300.0, "Overdue"), (400.0, "Draft")] {
            let i = Invoice(amount: amt); i.status = st; ctx.insert(i); i.job = j
        }
        XCTAssertEqual(j.invoiced, 1_000)
        XCTAssertEqual(j.collected, 100)
        XCTAssertEqual(j.outstanding, 500)       // Sent + Overdue only
    }

    func testCashSpentIncludesExpensesPaidPermitsAndLabor() {
        let j = job()
        let e = Expense(title: "x", amount: 100); ctx.insert(e); e.job = j
        let c = Contractor(name: "c"); c.value = 1_000; ctx.insert(c); c.job = j
        let pay = Payment(amount: 400); ctx.insert(pay); pay.contractor = c
        let p = Permit(trade: "Electrical"); p.cost = 50; ctx.insert(p); p.job = j
        XCTAssertEqual(j.cashSpent, 100 + 400 + 50)
        XCTAssertEqual(j.contractorTotal - j.contractorPaid, 600)   // still owed
    }

    func testPunchProgressPercent() {
        let j = job()
        XCTAssertEqual(j.percent, 0)
        for done in [true, true, false, false, false] {
            let p = PunchItem(text: "t", trade: "Plumbing"); p.done = done; ctx.insert(p); p.job = j
        }
        XCTAssertEqual(j.doneCount, 2)
        XCTAssertEqual(j.totalCount, 5)
        XCTAssertEqual(j.percent, 40)
    }

    func testSpaceOpenDoneCounts() {
        let j = job()
        let s = Space(name: "Kitchen"); ctx.insert(s); s.job = j
        for done in [true, false, false] {
            let p = PunchItem(text: "t", trade: "Carpentry"); p.done = done; ctx.insert(p); p.space = s; p.job = j
        }
        XCTAssertEqual(s.openCount, 2)
        XCTAssertEqual(s.doneCount, 1)
    }

    func testTimeEntryHoursRoundedToTwoDecimals() {
        let t = TimeEntry(worker: "Stan")
        t.clockIn = Date(timeIntervalSince1970: 0)
        t.clockOut = Date(timeIntervalSince1970: 5_400)     // 1.5 h
        t.rate = 40
        XCTAssertEqual(t.hours, 1.5, accuracy: 0.001)
        let j = job(); ctx.insert(t); t.job = j
        XCTAssertEqual(j.laborTotal, 60, accuracy: 0.001)
        XCTAssertEqual(j.laborHours, 1.5, accuracy: 0.001)
    }

    func testNegativeTimeIsClampedToZero() {
        let t = TimeEntry(worker: "x")
        t.clockIn = Date(timeIntervalSince1970: 100); t.clockOut = Date(timeIntervalSince1970: 0)
        XCTAssertEqual(t.hours, 0)
    }

    func testContractorOwedIsAgreedMinusPaid() {
        let c = Contractor(name: "x"); c.value = 900; ctx.insert(c)
        let p = Payment(amount: 250); ctx.insert(p); p.contractor = c
        XCTAssertEqual(c.paid, 250)
        XCTAssertEqual(c.owed, 650)
    }

    func testMoneyTextFormatting() {
        XCTAssertEqual(Money.text(1234.5), "$1,234.50")
        XCTAssertEqual(Money.text(-20), "-$20.00")
        XCTAssertEqual(Money.text(0), "$0.00")
    }
}
