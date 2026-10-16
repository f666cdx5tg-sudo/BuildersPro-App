import SwiftUI
import SwiftData

struct JobsView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @State private var newName = ""
    @State private var adding = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(jobs) { job in
                    NavigationLink(value: job) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(job.name).font(.headline).lineLimit(1)      // names never wrap
                            HStack {
                                ProgressView(value: Double(job.percent), total: 100)
                                Text("\(job.percent)%").font(.caption.bold())
                            }
                            Text("\(job.doneCount)/\(job.totalCount) done" +
                                 (job.totalCount > job.doneCount ? " · \(job.totalCount - job.doneCount) left" : ""))
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(jobs[$0]) } }
            }
            .navigationTitle("Jobs")
            .navigationDestination(for: Job.self) { JobDetailView(job: $0) }
            .toolbar {
                Button { adding = true } label: { Image(systemName: "plus") }
            }
            .alert("New job", isPresented: $adding) {
                TextField("Job name", text: $newName)
                Button("Add") {
                    let n = newName.trimmingCharacters(in: .whitespaces)
                    if !n.isEmpty { context.insert(Job(name: n)) }
                    newName = ""
                }
                Button("Cancel", role: .cancel) { newName = "" }
            }
            .overlay { if jobs.isEmpty { ContentUnavailableView("No jobs yet", systemImage: "hammer", description: Text("Tap + to add your first job.")) } }
        }
    }
}
