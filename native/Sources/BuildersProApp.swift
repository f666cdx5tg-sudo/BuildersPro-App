import SwiftUI
import SwiftData

@main
struct BuildersProApp: App {
    // iCloud sync: SwiftData mirrors this store to the private CloudKit container in the entitlements file.
    var container: ModelContainer = {
        let schema = Schema([Job.self, Space.self, PunchItem.self, SitePhoto.self])
        let config = ModelConfiguration(schema: schema, cloudKitDatabase: .automatic)
        do { return try ModelContainer(for: schema, configurations: [config]) }
        catch { fatalError("Could not open the database: \(error)") }
    }()

    var body: some Scene {
        WindowGroup { JobsView() }
            .modelContainer(container)
    }
}
