import SwiftUI
import SwiftData

@main
struct BuildersProApp: App {
    // iCloud sync: SwiftData mirrors this store to the private CloudKit container in the entitlements file.
    init() { UserDefaults.standard.removeObject(forKey: "bpActiveJob") }   // no job preselected on launch

    var container: ModelContainer = {
        let schema = Schema([Job.self, Space.self, PunchItem.self, SitePhoto.self,
                              Expense.self, Contractor.self, Payment.self, DailyReport.self,
                              ChangeOrder.self, Invoice.self, Permit.self, TimeEntry.self,
                              Appointment.self, JobNote.self, ShoppingItem.self, Vendor.self, JobDocument.self, PunchPhoto.self, Estimate.self, BookContact.self])
        #if targetEnvironment(simulator)
        let config = ModelConfiguration(schema: schema, cloudKitDatabase: .none)     // the simulator has no iCloud account — keep it local so it can launch
        #else
        let config = ModelConfiguration(schema: schema, cloudKitDatabase: .automatic)
        #endif
        do { return try ModelContainer(for: schema, configurations: [config]) }
        catch { fatalError("Could not open the database: \(error)") }
    }()

    var body: some Scene {
        WindowGroup { LockGate { RootShell() }.font(.title3).controlSize(.large) }
            .modelContainer(container)
    }
}
